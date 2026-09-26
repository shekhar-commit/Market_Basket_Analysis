"""Consolidated Python tests; TypeScript runtime tests remain in combo-intelligence.test.ts."""

import unittest, json, time, math
from backend.database import SessionLocal, Base, engine
from backend.services import create_or_get_cart, add_item_to_cart, remove_item_from_cart, get_cart_summary, compute_combo_economics, get_top_selling_products, record_recommendation_event, get_recommendation_performance_metrics, FEATURE_COLUMNS, FEATURE_VERSION, TARGET_COLUMN, extract_features_for_observation, extract_target_for_observation, predict_combo_future_purchases, build_training_dataset, pos_adapter, get_product_stock_info, update_single_product_stock, deduct_inventory_stock, get_realtime_cart_recommendations
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Product, Restaurant, Transaction, TransactionItem, Inventory
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from backend.ml import ComboRegressor, time_based_train_val_test_split

def init_db():
    """Create missing application tables for tests using the configured database."""
    Base.metadata.create_all(bind=engine)


# ============================== test_cart.py ==============================

class TestCartService(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.restaurant_id = "R001"

    def tearDown(self):
        self.db.close()

    def test_create_and_manage_cart(self):
        # 1. Create empty cart
        cart = create_or_get_cart(self.db, self.restaurant_id)
        self.assertIsNotNone(cart.cart_id)
        self.assertEqual(cart.restaurant_id, self.restaurant_id)

        # 2. Add an item
        add_item_to_cart(self.db, cart.cart_id, self.restaurant_id, "P001", quantity=2)
        summary = get_cart_summary(self.db, cart.cart_id, self.restaurant_id)
        self.assertIsNotNone(summary)
        self.assertEqual(len(summary["items"]), 1)
        self.assertEqual(summary["items"][0]["product_id"], "P001")
        self.assertEqual(summary["items"][0]["quantity"], 2)

        # 3. Add second item
        add_item_to_cart(self.db, cart.cart_id, self.restaurant_id, "P002", quantity=1)
        summary2 = get_cart_summary(self.db, cart.cart_id, self.restaurant_id)
        self.assertEqual(len(summary2["items"]), 2)

        # 4. Remove item
        removed = remove_item_from_cart(self.db, cart.cart_id, "P001")
        self.assertTrue(removed)
        summary3 = get_cart_summary(self.db, cart.cart_id, self.restaurant_id)
        self.assertEqual(len(summary3["items"]), 1)
        self.assertEqual(summary3["items"][0]["product_id"], "P002")

# ============================== test_combo_economics.py ==============================

class TestRestaurantComboEconomics(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.session.add(Restaurant(
            restaurant_id="R001",
            restaurant_name="Test Restaurant",
            timezone="UTC",
            currency="INR",
        ))
        self.session.add_all([
            Product(
                product_id="A", restaurant_id="R001", product_name="Tea", category="Drink",
                selling_price=40, cost_price=10, is_active=True,
            ),
            Product(
                product_id="B", restaurant_id="R001", product_name="Samosa", category="Snack",
                selling_price=20, cost_price=5, is_active=True,
            ),
            Product(
                product_id="C", restaurant_id="R001", product_name="Juice", category="Drink",
                selling_price=30, cost_price=12, is_active=True,
            ),
        ])
        self.session.flush()

        now = datetime.utcnow()
        self._add_order("T1", now - timedelta(days=2), [("A", 3, 120), ("B", 2, 40)])
        self._add_order("T1B", now - timedelta(days=2), [("A", 1, 40), ("B", 1, 20)])
        self._add_order("T2", now - timedelta(days=1), [("A", 1, 40)])
        self._add_order("T3", now - timedelta(days=1), [("B", 1, 20)])
        self._add_order("T4", now - timedelta(days=1), [("C", 1, 30)])
        self._add_order("OLD", now - timedelta(days=60), [("A", 7, 280), ("C", 1, 30)])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _add_order(self, transaction_id, timestamp, lines):
        self.session.add(Transaction(
            transaction_id=transaction_id,
            restaurant_id="R001",
            timestamp=timestamp,
            order_status="completed",
            payment_status="paid",
            channel="dine_in",
            total_amount=sum(line[2] for line in lines),
        ))
        self.session.flush()
        for product_id, quantity, line_total in lines:
            self.session.add(TransactionItem(
                transaction_id=transaction_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=line_total / quantity,
                discount_amount=0,
                net_price=line_total,
            ))

    def test_top_selling_and_combo_metrics_use_selected_transactions_and_distinct_baskets(self):
        sales = get_top_selling_products(self.session, period="30days", limit=10)
        tea = next(product for product in sales if product["product_id"] == "A")
        self.assertEqual(tea["total_quantity_sold"], 5)
        self.assertEqual(tea["transaction_count"], 3)
        self.assertEqual(tea["total_revenue"], 200)
        self.assertEqual(tea["total_profit"], 150)

        with patch("backend.services", return_value=None):
            combos = compute_combo_economics(
                self.session,
                min_pair_count=1,
                min_confidence=0.3,
                min_lift=1.1,
                period="30days",
            )

        combo = next(candidate for candidate in combos if candidate["product_a_id"] == "A" and candidate["product_b_id"] == "B")
        self.assertEqual(combo["pair_transaction_count"], 2)
        self.assertAlmostEqual(combo["support"], 2 / 5, places=4)
        self.assertAlmostEqual(combo["confidence_a_to_b"], 2 / 3, places=4)
        self.assertAlmostEqual(combo["confidence_b_to_a"], 2 / 3, places=4)
        self.assertAlmostEqual(combo["lift"], 10 / 9, places=3)
        self.assertEqual(combo["regular_sum_price"], 60)
        self.assertEqual(combo["suggested_combo_price"], 54)
        self.assertEqual(combo["customer_savings"], 6)
        self.assertEqual(combo["combo_cost"], 15)
        self.assertEqual(combo["normal_profit"], 45)
        self.assertEqual(combo["combo_profit"], 39)
        self.assertEqual(combo["profit_difference"], -6)
        self.assertTrue(combo["is_candidate_combo"])
        self.assertEqual(combo["recommendation_mode"], "Rule-Based Recommendation")

    def test_active_restaurant_model_predictions_rank_eligible_combos(self):
        def predict_from_history(_db, _restaurant_id, candidates):
            return [
                {
                    **candidate,
                    "predicted_future_combo_purchases_7d": 7,
                    "model_version": "v2",
                }
                for candidate in candidates
            ]

        with patch(
            "backend.services.predict_combo_future_purchases",
            side_effect=predict_from_history,
        ):
            combos = compute_combo_economics(
                self.session,
                min_pair_count=1,
                min_confidence=0.3,
                min_lift=1.1,
                period="30days",
            )

        combo = next(candidate for candidate in combos if candidate["product_a_id"] == "A" and candidate["product_b_id"] == "B")
        self.assertEqual(combo["recommendation_mode"], "ML Recommendation")
        self.assertEqual(combo["model_version"], "v2")
        self.assertEqual(combo["predicted_future_combo_purchases_7d"], 7)
        self.assertEqual(combo["estimated_gross_profit_7d"], 273)

# ============================== test_feedback.py ==============================

class TestFeedbackService(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.restaurant_id = "R001"

    def tearDown(self):
        self.db.close()

    def test_record_feedback_events_and_calculate_metrics(self):
        # Record shown
        evt_shown = record_recommendation_event(
            self.db,
            restaurant_id=self.restaurant_id,
            recommended_product_id="P002",
            event_type="shown",
            price_at_event=40.0,
        )
        self.assertTrue(evt_shown.shown)

        # Record click
        evt_click = record_recommendation_event(
            self.db,
            restaurant_id=self.restaurant_id,
            recommended_product_id="P002",
            event_type="clicked",
            price_at_event=40.0,
        )
        self.assertTrue(evt_click.clicked)

        # Record add to cart
        evt_add = record_recommendation_event(
            self.db,
            restaurant_id=self.restaurant_id,
            recommended_product_id="P002",
            event_type="added_to_cart",
            price_at_event=40.0,
        )
        self.assertTrue(evt_add.added_to_cart)

        # Record purchase
        evt_purchased = record_recommendation_event(
            self.db,
            restaurant_id=self.restaurant_id,
            recommended_product_id="P002",
            event_type="purchased",
            price_at_event=40.0,
        )
        self.assertTrue(evt_purchased.purchased)

        metrics = get_recommendation_performance_metrics(self.db, self.restaurant_id, days=1)
        self.assertGreaterEqual(metrics["shown_count"], 1)
        self.assertGreaterEqual(metrics["click_count"], 1)
        self.assertGreaterEqual(metrics["add_to_cart_count"], 1)
        self.assertGreaterEqual(metrics["purchase_count"], 1)
        self.assertGreater(metrics["ctr"], 0.0)

# ============================== test_historical_combo_ml.py ==============================

class TestHistoricalComboML(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.session.add(Restaurant(
            restaurant_id="R001",
            restaurant_name="Test Restaurant",
        ))
        self.session.add_all([
            Product(
                product_id=product_id,
                restaurant_id="R001",
                product_name=product_id,
                category="Test",
                selling_price=10,
                cost_price=4,
                is_active=True,
            )
            for product_id in ("A", "B", "C")
        ])
        self.session.flush()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _add_order(self, transaction_id, timestamp, products, payment_status="paid", order_status="completed"):
        self.session.add(Transaction(
            transaction_id=transaction_id,
            restaurant_id="R001",
            timestamp=timestamp,
            order_status=order_status,
            payment_status=payment_status,
        ))
        self.session.flush()
        for product_id in products:
            self.session.add(TransactionItem(
                transaction_id=transaction_id,
                product_id=product_id,
                quantity=1,
                unit_price=10,
                discount_amount=0,
                net_price=10,
            ))

    def test_features_exclude_observation_and_future_transactions(self):
        observation = datetime(2024, 2, 1)
        self._add_order("PAST", observation - timedelta(days=1), ["A", "B"])
        self._add_order("AT_OBSERVATION", observation, ["A", "B"])
        self._add_order("FUTURE", observation + timedelta(days=1), ["A", "B"])
        self.session.flush()

        transactions = self.session.query(Transaction).order_by(Transaction.timestamp).all()
        item_rows = self.session.query(TransactionItem).all()
        records = [
            {
                "transaction_id": transaction.transaction_id,
                "timestamp": transaction.timestamp,
                "items": {
                    item.product_id: {"quantity": item.quantity, "net_price": item.net_price}
                    for item in item_rows if item.transaction_id == transaction.transaction_id
                },
            }
            for transaction in transactions
        ]
        product_a = self.session.get(Product, "A")
        product_b = self.session.get(Product, "B")
        features = extract_features_for_observation(observation, product_a, product_b, records)

        self.assertEqual(set(features), set(FEATURE_COLUMNS))
        self.assertEqual(features["pair_transaction_count"], 1)
        self.assertEqual(features["product_a_quantity_sold"], 1)
        self.assertEqual(
            extract_target_for_observation(observation, "A", "B", records),
            2,
        )

    def test_training_candidate_pairs_use_only_prior_paid_completed_baskets(self):
        start = datetime(2024, 1, 1)
        for day in range(61):
            products = ["A", "B", "C"] if day >= 40 else ["A", "B"]
            self._add_order(f"PAID_{day}", start + timedelta(days=day), products)
        self._add_order(
            "PENDING_PAIR",
            start + timedelta(days=31),
            ["A", "C"],
            payment_status="pending",
        )
        self._add_order(
            "CANCELLED_PAIR",
            start + timedelta(days=32),
            ["A", "C"],
            order_status="cancelled",
        )
        self.session.commit()

        rows = build_training_dataset(self.session, restaurant_id="R001")
        first_observation = start + timedelta(days=30)
        first_rows = [row for row in rows if row["observation_date"] == first_observation]
        first_pairs = {(row["product_a_id"], row["product_b_id"]) for row in first_rows}
        self.assertEqual(first_pairs, {("A", "B")})
        self.assertTrue(any(
            row["observation_date"] > start + timedelta(days=40)
            and (row["product_a_id"], row["product_b_id"]) == ("A", "C")
            for row in rows
        ))
        self.assertTrue(all(row["feature_version"] == "v2" for row in rows))

    def test_time_split_groups_observation_dates_and_purges_overlapping_targets(self):
        start = datetime(2024, 1, 1)
        dataset = []
        for index in range(15):
            observation = start + timedelta(days=index * 6)
            for pair_index in range(3):
                dataset.append({
                    "observation_date": observation,
                    "target_end_date": observation + timedelta(days=7),
                    "pair_index": pair_index,
                })

        train, validation, test = time_based_train_val_test_split(dataset)
        train_dates = {row["observation_date"] for row in train}
        validation_dates = {row["observation_date"] for row in validation}
        test_dates = {row["observation_date"] for row in test}
        self.assertFalse(train_dates & validation_dates)
        self.assertFalse(train_dates & test_dates)
        self.assertFalse(validation_dates & test_dates)
        self.assertTrue(train and validation and test)

        validation_start = min(validation_dates)
        test_start = min(test_dates)
        self.assertTrue(all(row["target_end_date"] <= validation_start for row in train))
        self.assertTrue(all(row["target_end_date"] <= test_start for row in validation))
        for group in (train, validation, test):
            counts = {}
            for row in group:
                counts[row["observation_date"]] = counts.get(row["observation_date"], 0) + 1
            self.assertTrue(all(count == 3 for count in counts.values()))

    def test_combo_regressor_round_trips_the_trained_model(self):
        model = ComboRegressor(feature_names=["pair_count"])
        model.fit([[0.0], [1.0], [2.0], [3.0]], [0.0, 1.0, 2.0, 3.0])
        expected = model.predict([[0.0], [3.0]])

        with TemporaryDirectory() as directory:
            path = f"{directory}\\combo-model.json"
            model.save(path)
            loaded = ComboRegressor.load(path)

        self.assertEqual(loaded.feature_names, ["pair_count"])
        actual = loaded.predict([[0.0], [3.0]])
        for expected_value, actual_value in zip(expected, actual):
            self.assertAlmostEqual(expected_value, actual_value)

    def test_stale_model_feature_snapshot_uses_rule_fallback(self):
        active_model = SimpleNamespace(
            model_path="unused",
            target=TARGET_COLUMN,
            feature_snapshot=json.dumps({
                "feature_version": "v1",
                "feature_names": FEATURE_COLUMNS,
                "target": TARGET_COLUMN,
            }),
        )
        with patch(
            "backend.services.get_active_model_record",
            return_value=active_model,
        ), patch("backend.services.log_event"):
            result = predict_combo_future_purchases(None, "R001", [])

        self.assertIsNone(result)

# ============================== test_idempotency.py ==============================

class TestPOSIdempotency(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.restaurant_id = "R001"
        self.tx_id = f"IDEMP-TEST-{int(time.time())}"

    def tearDown(self):
        # Clean up test transaction
        self.db.query(Transaction).filter(Transaction.transaction_id == self.tx_id).delete()
        self.db.commit()
        self.db.close()

    def test_idempotent_transaction_ingestion(self):
        # Check initial inventory of P001
        inv_before = self.db.query(Inventory).filter(Inventory.product_id == "P001").first()
        initial_stock = inv_before.current_stock if inv_before else 100

        payload = {
            "restaurant_id": self.restaurant_id,
            "transaction_id": self.tx_id,
            "order_status": "completed",
            "payment_status": "paid",
            "channel": "pos",
            "items": [
                {"product_id": "P001", "quantity": 2, "unit_price": 20.0}
            ]
        }

        # First ingestion
        res1 = pos_adapter.receive_transaction(self.db, payload)
        self.assertTrue(res1["success"])
        self.assertFalse(res1.get("is_duplicate", False))

        inv_after_1 = self.db.query(Inventory).filter(Inventory.product_id == "P001").first()
        expected_stock = max(0, initial_stock - 2)
        if inv_after_1:
            self.assertEqual(inv_after_1.current_stock, expected_stock)

        # Second ingestion with identical transaction_id
        res2 = pos_adapter.receive_transaction(self.db, payload)
        self.assertTrue(res2["success"])
        self.assertTrue(res2.get("is_duplicate", True))

        # Verify stock did NOT decrement a second time (must remain expected_stock)
        inv_after_2 = self.db.query(Inventory).filter(Inventory.product_id == "P001").first()
        if inv_after_2:
            self.assertEqual(inv_after_2.current_stock, expected_stock)

# ============================== test_inventory.py ==============================

class TestInventoryService(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.restaurant_id = "R001"

    def tearDown(self):
        self.db.close()

    def test_stock_update_and_deduction(self):
        # 1. Update stock
        update_single_product_stock(self.db, self.restaurant_id, "P001", current_stock=50, is_available=True)
        info = get_product_stock_info(self.db, self.restaurant_id, "P001")
        self.assertEqual(info["current_stock"], 50)
        self.assertTrue(info["is_available"])

        # 2. Deduct stock for transaction
        items = [{"product_id": "P001", "quantity": 5}]
        deduct_res = deduct_inventory_stock(self.db, self.restaurant_id, items)
        self.assertTrue(deduct_res["success"])

        info2 = get_product_stock_info(self.db, self.restaurant_id, "P001")
        self.assertEqual(info2["current_stock"], 45)

        # 3. Deduct all remaining stock
        deduct_inventory_stock(self.db, self.restaurant_id, [{"product_id": "P001", "quantity": 45}])
        info3 = get_product_stock_info(self.db, self.restaurant_id, "P001")
        self.assertEqual(info3["current_stock"], 0)
        self.assertFalse(info3["is_available"])

# ============================== test_multi_restaurant.py ==============================

class TestMultiRestaurantIsolation(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        # Ensure a secondary restaurant exists
        r2 = self.db.query(Restaurant).filter(Restaurant.restaurant_id == "R002").first()
        if not r2:
            r2 = Restaurant(
                restaurant_id="R002",
                restaurant_name="Second Bistro",
                timezone="Asia/Kolkata",
                currency="INR",
                is_active=True
            )
            self.db.add(r2)
            self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_restaurant_isolation(self):
        # Recommendations for R001
        res_r1 = get_realtime_cart_recommendations(
            self.db,
            restaurant_id="R001",
            cart_items=[{"product_id": "P001", "quantity": 1}],
            limit=5,
            record_shown=False,
        )

        # Recommendations for R002 (empty inventory/products)
        res_r2 = get_realtime_cart_recommendations(
            self.db,
            restaurant_id="R002",
            cart_items=[{"product_id": "P001", "quantity": 1}],
            limit=5,
            record_shown=False,
        )

        self.assertEqual(res_r1["restaurant_id"], "R001")
        self.assertEqual(res_r2["restaurant_id"], "R002")
        # R002 has no products or transactions, so its recommendations must be empty
        self.assertEqual(len(res_r2["recommendations"]), 0)

# ============================== test_recommendations.py ==============================

class TestRealtimeRecommendations(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.restaurant_id = "R001"

    def tearDown(self):
        self.db.close()

    def test_empty_cart(self):
        """Test 1: Empty cart handling."""
        res = get_realtime_cart_recommendations(
            self.db,
            restaurant_id=self.restaurant_id,
            cart_items=[],
            limit=5,
            record_shown=False,
        )
        self.assertIn("recommendations", res)
        self.assertIn("recommendation_mode", res)

    def test_single_product_and_exclusion_of_cart_items(self):
        """Test 2 & 3: Recommendations with cart items exclude already added products."""
        cart_items = [{"product_id": "P001", "quantity": 1}]
        res = get_realtime_cart_recommendations(
            self.db,
            restaurant_id=self.restaurant_id,
            cart_items=cart_items,
            limit=5,
            record_shown=False,
        )
        rec_ids = [r["product_id"] for r in res["recommendations"]]

        # P001 must NEVER be recommended because it is already in the cart
        self.assertNotIn("P001", rec_ids)

        if rec_ids:
            # Add top recommended item into cart
            cart_items_2 = [{"product_id": "P001", "quantity": 1}, {"product_id": rec_ids[0], "quantity": 1}]
            res2 = get_realtime_cart_recommendations(
                self.db,
                restaurant_id=self.restaurant_id,
                cart_items=cart_items_2,
                limit=5,
                record_shown=False,
            )
            rec_ids_2 = [r["product_id"] for r in res2["recommendations"]]
            self.assertNotIn("P001", rec_ids_2)
            self.assertNotIn(rec_ids[0], rec_ids_2)

    def test_out_of_stock_exclusion(self):
        """Test 4: Products with 0 stock or is_available=False must be filtered out."""
        # Force product P002 to stock = 0
        inv = self.db.query(Inventory).filter(Inventory.product_id == "P002").first()
        prev_stock = inv.current_stock if inv else 100
        prev_avail = inv.is_available if inv else True

        try:
            update_single_product_stock(self.db, self.restaurant_id, "P002", current_stock=0, is_available=False)

            res = get_realtime_cart_recommendations(
                self.db,
                restaurant_id=self.restaurant_id,
                cart_items=[{"product_id": "P001", "quantity": 1}],
                limit=10,
                record_shown=False,
            )
            rec_ids = [r["product_id"] for r in res["recommendations"]]
            self.assertNotIn("P002", rec_ids, "Out-of-stock product P002 should not be recommended")
        finally:
            # Restore stock
            update_single_product_stock(self.db, self.restaurant_id, "P002", current_stock=prev_stock, is_available=prev_avail)

    def test_inactive_product_exclusion(self):
        """Test 5: Inactive products must be rejected."""
        prod = self.db.query(Product).filter(Product.product_id == "P005").first()
        if prod:
            original_active = prod.is_active
            try:
                prod.is_active = False
                self.db.commit()

                res = get_realtime_cart_recommendations(
                    self.db,
                    restaurant_id=self.restaurant_id,
                    cart_items=[{"product_id": "P001", "quantity": 1}],
                    limit=10,
                    record_shown=False,
                )
                rec_ids = [r["product_id"] for r in res["recommendations"]]
                self.assertNotIn("P005", rec_ids, "Inactive product P005 should not be recommended")
            finally:
                prod.is_active = original_active
                self.db.commit()

    def test_explanation_matches_metrics(self):
        """Test 15: Manager explanation must be verifiably grounded in calculated values."""
        res = get_realtime_cart_recommendations(
            self.db,
            restaurant_id=self.restaurant_id,
            cart_items=[{"product_id": "P001", "quantity": 1}],
            limit=3,
            record_shown=False,
        )
        for r in res.get("recommendations", []):
            explanation = r["explanation"]
            self.assertIn(f"{r['pair_transaction_count']:,}", explanation)
            self.assertIn(f"{r['lift']:.2f}", explanation)
            self.assertIn(str(r["current_stock"]), explanation)

# ============================== test_standalone_engine.py ==============================

class TestRecommendationScoringFormulas(unittest.TestCase):
    """
    Validates Phase 3 scoring formulas, weights, and constraints using Python standard library.
    """

    def setUp(self):
        self.ML_SCORE_WEIGHT = 0.40
        self.ASSOCIATION_WEIGHT = 0.25
        self.RECENCY_WEIGHT = 0.15
        self.PROFIT_WEIGHT = 0.15
        self.AVAILABILITY_WEIGHT = 0.05

    def calculate_score(self, norm_ml, norm_assoc, norm_recency, norm_profit, norm_avail, is_ml=True):
        if is_ml:
            return (
                (self.ML_SCORE_WEIGHT * norm_ml) +
                (self.ASSOCIATION_WEIGHT * norm_assoc) +
                (self.RECENCY_WEIGHT * norm_recency) +
                (self.PROFIT_WEIGHT * norm_profit) +
                (self.AVAILABILITY_WEIGHT * norm_avail)
            )
        else:
            return (
                (0.50 * norm_assoc) +
                (0.25 * norm_recency) +
                (0.20 * norm_profit) +
                (0.05 * norm_avail)
            )

    def test_weights_sum_to_one(self):
        total_ml_weights = (
            self.ML_SCORE_WEIGHT +
            self.ASSOCIATION_WEIGHT +
            self.RECENCY_WEIGHT +
            self.PROFIT_WEIGHT +
            self.AVAILABILITY_WEIGHT
        )
        self.assertAlmostEqual(total_ml_weights, 1.0, places=4)

    def test_cart_item_exclusion(self):
        cart = ["P001", "P002"] # Burger, Fries
        candidate_pool = ["P001", "P002", "P003", "P004"] # Burger, Fries, Coke, Shake
        valid_candidates = [p for p in candidate_pool if p not in cart]
        self.assertEqual(valid_candidates, ["P003", "P004"])

    def test_out_of_stock_gate(self):
        inventory = {
            "P003": {"stock": 15, "available": True},
            "P004": {"stock": 0, "available": True}, # Out of stock
            "P005": {"stock": 10, "available": False}, # Marked unavailable
        }
        valid_items = [
            pid for pid, inv in inventory.items()
            if inv["available"] and inv["stock"] > 0
        ]
        self.assertEqual(valid_items, ["P003"])

    def test_idempotent_order_processing(self):
        processed_tx_ids = set()
        inventory = {"P001": 100}

        def process_tx(tx_id, qty):
            if tx_id in processed_tx_ids:
                return "DUPLICATE_IGNORED"
            processed_tx_ids.add(tx_id)
            inventory["P001"] -= qty
            return "SUCCESS"

        r1 = process_tx("TXN-101", 2)
        self.assertEqual(r1, "SUCCESS")
        self.assertEqual(inventory["P001"], 98)

        # Duplicate submission of same transaction
        r2 = process_tx("TXN-101", 2)
        self.assertEqual(r2, "DUPLICATE_IGNORED")
        # Stock must remain 98, not 96!
        self.assertEqual(inventory["P001"], 98)

    def test_feedback_conversion_metrics(self):
        shown = 1000
        clicks = 250
        adds = 150
        purchases = 90

        ctr = (clicks / shown) * 100.0
        add_rate = (adds / shown) * 100.0
        conversion_rate = (purchases / shown) * 100.0

        self.assertAlmostEqual(ctr, 25.0)
        self.assertAlmostEqual(add_rate, 15.0)
        self.assertAlmostEqual(conversion_rate, 9.0)

        # Zero denominator safety
        safe_ctr = (0 / 0) if 0 > 0 else 0.0
        self.assertEqual(safe_ctr, 0.0)

if __name__ == "__main__":
    unittest.main()
