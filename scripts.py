"""Explicit command entry points for the project's optional data and model scripts."""
import argparse
import sys

def generate_demo_data(num_transactions=1500, output_file="data/demo_transactions.csv"):
    """Generate demo POS transaction data on explicit invocation."""
    import csv
    import random
    from datetime import datetime, timedelta

    """
    Generates realistic restaurant POS transaction dataset.
    Simulates natural co-purchasing affinities:
      - Tea + Samosa (High lift afternoon/morning snack)
      - Burger + French Fries + Coke (Classic meal bundle)
      - Pizza + Garlic Bread + Cold Drink (Dinner bundle)
      - Biryani + Raita (Main course combo)
      - Momos + Cold Drink
    Channels: dine_in (45%), takeaway (25%), delivery (20%), online (10%)
    Statuses: completed (96%), cancelled (2.5%), refunded (1.5%)
    """

    PRODUCTS = [
        {"id": "P001", "name": "Masala Tea", "category": "Beverage", "price": 20, "cost": 8},
        {"id": "P002", "name": "Crispy Samosa", "category": "Snacks", "price": 15, "cost": 6},
        {"id": "P003", "name": "Filter Coffee", "category": "Beverage", "price": 35, "cost": 12},
        {"id": "P004", "name": "Mixed Veg Pakora", "category": "Snacks", "price": 40, "cost": 16},
        {"id": "P005", "name": "Grilled Veg Sandwich", "category": "Snacks", "price": 60, "cost": 25},
        {"id": "P006", "name": "Classic Burger", "category": "Fast Food", "price": 120, "cost": 50},
        {"id": "P007", "name": "French Fries", "category": "Fast Food", "price": 70, "cost": 20},
        {"id": "P008", "name": "Chilled Coke", "category": "Beverage", "price": 40, "cost": 18},
        {"id": "P009", "name": "Cheese Margherita Pizza", "category": "Pizza", "price": 220, "cost": 85},
        {"id": "P010", "name": "Cheesy Garlic Bread", "category": "Sides", "price": 90, "cost": 32},
        {"id": "P011", "name": "Steamed Momos", "category": "Snacks", "price": 110, "cost": 42},
        {"id": "P012", "name": "Cold Drink (Thums Up)", "category": "Beverage", "price": 35, "cost": 15},
        {"id": "P013", "name": "Paneer Kathi Roll", "category": "Rolls", "price": 130, "cost": 52},
        {"id": "P014", "name": "Paneer Tikka Platter", "category": "Starters", "price": 180, "cost": 75},
        {"id": "P015", "name": "Chicken Dum Biryani", "category": "Main Course", "price": 240, "cost": 105},
        {"id": "P016", "name": "Cucumber Mint Raita", "category": "Sides", "price": 50, "cost": 15},
    ]

    PROD_BY_ID = {p["id"]: p for p in PRODUCTS}

    AFFINITY_BUNDLES = [
        # Tea + Samosa
        {"primary": "P001", "companions": ["P002"], "prob": 0.62},
        # Coffee + Sandwich
        {"primary": "P003", "companions": ["P005"], "prob": 0.48},
        # Burger + Fries + Coke
        {"primary": "P006", "companions": ["P007", "P008"], "prob": 0.72},
        # Pizza + Garlic Bread + Cold Drink
        {"primary": "P009", "companions": ["P010", "P012"], "prob": 0.58},
        # Biryani + Raita
        {"primary": "P015", "companions": ["P016"], "prob": 0.65},
        # Momos + Cold Drink
        {"primary": "P011", "companions": ["P012"], "prob": 0.44},
        # Roll + Cold Drink
        {"primary": "P013", "companions": ["P012"], "prob": 0.38},
    ]

    CHANNELS = ["dine_in", "dine_in", "dine_in", "takeaway", "takeaway", "delivery", "online"]

    def _generate_transactions(num_transactions=1500, output_file="data/demo_transactions.csv"):
        random.seed(42)
        end_date = datetime(2026, 9, 24, 20, 0, 0)
        start_date = end_date - timedelta(days=45)
        total_seconds = int((end_date - start_date).total_seconds())

        rows = []
        for i in range(1, num_transactions + 1):
            tx_id = f"TX{i:05d}"
            restaurant_id = "R001"
            cust_id = f"CUST{random.randint(100, 999)}"
            tx_time = start_date + timedelta(seconds=random.randint(0, total_seconds))
            timestamp_iso = tx_time.strftime("%Y-%m-%d %H:%M:%S")

            # Status distribution: 96% completed, 2.5% cancelled, 1.5% refunded
            roll = random.random()
            if roll < 0.025:
                order_status = "cancelled"
                payment_status = "failed"
            elif roll < 0.040:
                order_status = "refunded"
                payment_status = "paid"
            else:
                order_status = "completed"
                payment_status = "paid"

            channel = random.choice(CHANNELS)

            # Decide items in basket
            basket_items = []
            # pick a primary affinity or random base product
            if random.random() < 0.70:
                affinity = random.choice(AFFINITY_BUNDLES)
                basket_items.append(affinity["primary"])
                for comp in affinity["companions"]:
                    if random.random() < affinity["prob"]:
                        basket_items.append(comp)
            else:
                sample_count = random.choices([1, 2, 3, 4], weights=[0.4, 0.4, 0.15, 0.05])[0]
                basket_items = random.sample([p["id"] for p in PRODUCTS], sample_count)

            # Ensure no duplicates in basket
            basket_items = list(dict.fromkeys(basket_items))
            if not basket_items:
                basket_items = ["P001"]

            # Compute transaction amounts
            tx_total = 0
            for pid in basket_items:
                prod = PROD_BY_ID[pid]
                qty = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03])[0]
                unit_price = prod["price"]
                item_discount = 0.0
                net_price = unit_price * qty - item_discount
                tx_total += net_price

                rows.append({
                    "transaction_id": tx_id,
                    "restaurant_id": restaurant_id,
                    "customer_id": cust_id,
                    "timestamp": timestamp_iso,
                    "order_status": order_status,
                    "payment_status": payment_status,
                    "channel": channel,
                    "product_id": pid,
                    "product_name": prod["name"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "item_discount": item_discount,
                    "net_price": net_price,
                })

        # Write to CSV
        fieldnames = [
            "transaction_id", "restaurant_id", "customer_id", "timestamp",
            "order_status", "payment_status", "channel",
            "product_id", "product_name", "quantity", "unit_price",
            "item_discount", "net_price"
        ]
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Generated {len(rows)} items across {num_transactions} transactions into {output_file}")
    return _generate_transactions(num_transactions, output_file)


def seed_database():
    """Reset and populate the demo SQLite database on explicit invocation."""
    import csv
    import os
    import sqlite3
    from datetime import datetime

    DB_FILE = "restaurant_intelligence.db"
    CSV_FILE = "data/demo_transactions.csv"

    INITIAL_RESTAURANT = (
        "R001",
        "The Grand Rasoi & Bistro",
        "Asia/Kolkata",
        "INR",
        datetime(2025, 1, 1).strftime("%Y-%m-%d %H:%M:%S"),
        1,
    )

    PRODUCTS = [
        ("P001", "R001", "Masala Tea", "Beverage", 20.0, 8.0, 1),
        ("P002", "R001", "Crispy Samosa", "Snacks", 15.0, 6.0, 1),
        ("P003", "R001", "Filter Coffee", "Beverage", 35.0, 12.0, 1),
        ("P004", "R001", "Mixed Veg Pakora", "Snacks", 40.0, 16.0, 1),
        ("P005", "R001", "Grilled Veg Sandwich", "Snacks", 60.0, 25.0, 1),
        ("P006", "R001", "Classic Burger", "Fast Food", 120.0, 50.0, 1),
        ("P007", "R001", "French Fries", "Fast Food", 70.0, 20.0, 1),
        ("P008", "R001", "Chilled Coke", "Beverage", 40.0, 18.0, 1),
        ("P009", "R001", "Cheese Margherita Pizza", "Pizza", 220.0, 85.0, 1),
        ("P010", "R001", "Cheesy Garlic Bread", "Sides", 90.0, 32.0, 1),
        ("P011", "R001", "Steamed Momos", "Snacks", 110.0, 42.0, 1),
        ("P012", "R001", "Cold Drink (Thums Up)", "Beverage", 35.0, 15.0, 1),
        ("P013", "R001", "Paneer Kathi Roll", "Rolls", 130.0, 52.0, 1),
        ("P014", "R001", "Paneer Tikka Platter", "Starters", 180.0, 75.0, 1),
        ("P015", "R001", "Chicken Dum Biryani", "Main Course", 240.0, 105.0, 1),
        ("P016", "R001", "Cucumber Mint Raita", "Sides", 50.0, 15.0, 1),
    ]

    INVENTORY = [
        ("P001", 320, 40, 1),
        ("P002", 180, 30, 1),
        ("P003", 210, 30, 1),
        ("P004", 95, 25, 1),
        ("P005", 110, 20, 1),
        ("P006", 140, 25, 1),
        ("P007", 250, 50, 1),
        ("P008", 300, 50, 1),
        ("P009", 85, 15, 1),
        ("P010", 90, 20, 1),
        ("P011", 12, 20, 1),   # Low stock
        ("P012", 280, 50, 1),
        ("P013", 75, 20, 1),
        ("P014", 60, 15, 1),
        ("P015", 130, 25, 1),
        ("P016", 110, 20, 1),
    ]

    def _seed_database_impl():
        print(f"Connecting to SQLite database at {DB_FILE}...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create schema tables if not exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            restaurant_id VARCHAR(50) PRIMARY KEY,
            restaurant_name VARCHAR(150) NOT NULL,
            timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
            currency VARCHAR(10) DEFAULT 'INR',
            created_at DATETIME,
            is_active BOOLEAN DEFAULT 1
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR(50) PRIMARY KEY,
            restaurant_id VARCHAR(50) NOT NULL,
            product_name VARCHAR(150) NOT NULL,
            category VARCHAR(50) NOT NULL,
            selling_price FLOAT NOT NULL,
            cost_price FLOAT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(restaurant_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            product_id VARCHAR(50) PRIMARY KEY,
            current_stock INTEGER DEFAULT 100,
            minimum_stock INTEGER DEFAULT 20,
            is_available BOOLEAN DEFAULT 1,
            last_restocked_at DATETIME,
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR(50) PRIMARY KEY,
            restaurant_id VARCHAR(50) NOT NULL,
            customer_id VARCHAR(50),
            timestamp DATETIME,
            order_status VARCHAR(30) DEFAULT 'completed',
            payment_status VARCHAR(30) DEFAULT 'paid',
            channel VARCHAR(30) DEFAULT 'dine_in',
            total_amount FLOAT DEFAULT 0.0,
            discount_amount FLOAT DEFAULT 0.0,
            created_at DATETIME,
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(restaurant_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_items (
            transaction_id VARCHAR(50) NOT NULL,
            product_id VARCHAR(50) NOT NULL,
            quantity INTEGER DEFAULT 1,
            unit_price FLOAT NOT NULL,
            discount_amount FLOAT DEFAULT 0.0,
            net_price FLOAT NOT NULL,
            PRIMARY KEY(transaction_id, product_id),
            FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id),
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        );
        """)

        # Clean existing
        cursor.execute("DELETE FROM transaction_items;")
        cursor.execute("DELETE FROM transactions;")
        cursor.execute("DELETE FROM inventory;")
        cursor.execute("DELETE FROM products;")
        cursor.execute("DELETE FROM restaurants;")

        # Seed restaurant
        cursor.execute(
            "INSERT INTO restaurants (restaurant_id, restaurant_name, timezone, currency, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?);",
            INITIAL_RESTAURANT,
        )

        # Seed products
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        for p in PRODUCTS:
            cursor.execute(
                "INSERT INTO products (product_id, restaurant_id, product_name, category, selling_price, cost_price, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (p[0], p[1], p[2], p[3], p[4], p[5], p[6], now_str, now_str),
            )

        # Seed inventory
        for inv in INVENTORY:
            cursor.execute(
                "INSERT INTO inventory (product_id, current_stock, minimum_stock, is_available, last_restocked_at) VALUES (?, ?, ?, ?, ?);",
                (inv[0], inv[1], inv[2], inv[3], now_str),
            )

        # Seed transactions from CSV
        if not os.path.exists(CSV_FILE):
            print(f"Error: {CSV_FILE} not found. Run `python scripts.py generate-demo-data` first.")
            return

        print(f"Reading {CSV_FILE}...")
        tx_map = {}
        items_list = []

        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tx_id = row["transaction_id"]
                if tx_id not in tx_map:
                    tx_map[tx_id] = {
                        "transaction_id": tx_id,
                        "restaurant_id": row["restaurant_id"],
                        "customer_id": row["customer_id"],
                        "timestamp": row["timestamp"],
                        "order_status": row["order_status"],
                        "payment_status": row["payment_status"],
                        "channel": row["channel"],
                        "total_amount": 0.0,
                        "discount_amount": 0.0,
                        "created_at": row["timestamp"],
                    }

                net_p = float(row["net_price"])
                tx_map[tx_id]["total_amount"] += net_p

                items_list.append((
                    tx_id,
                    row["product_id"],
                    int(row["quantity"]),
                    float(row["unit_price"]),
                    float(row["item_discount"]),
                    net_p,
                ))

        # Insert transactions
        for tx in tx_map.values():
            cursor.execute(
                """INSERT INTO transactions
                (transaction_id, restaurant_id, customer_id, timestamp, order_status, payment_status, channel, total_amount, discount_amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    tx["transaction_id"],
                    tx["restaurant_id"],
                    tx["customer_id"],
                    tx["timestamp"],
                    tx["order_status"],
                    tx["payment_status"],
                    tx["channel"],
                    round(tx["total_amount"], 2),
                    tx["discount_amount"],
                    tx["created_at"],
                ),
            )

        # Insert items
        cursor.executemany(
            """INSERT OR REPLACE INTO transaction_items
            (transaction_id, product_id, quantity, unit_price, discount_amount, net_price)
            VALUES (?, ?, ?, ?, ?, ?);""",
            items_list,
        )

        conn.commit()
        conn.close()
        print(f"Successfully seeded database: {len(tx_map)} transactions, {len(items_list)} items into {DB_FILE}")
    return _seed_database_impl()


def simulate_pos_stream(argv=None):
    """Run the existing POS-stream simulator with its usual CLI arguments."""
    #!/usr/bin/env python3
    """
    scripts.py simulate-pos-stream - Simulates an active POS transaction stream.
    Demonstrates:
      1. Streaming realistic multi-item customer orders into database
      2. Tracking transaction increments against the auto-retraining threshold (e.g. 10,000 new txs)
      3. Seamless model retraining triggering without service downtime
    Usage:
        python scripts.py simulate-pos-stream [--count 50] [--delay 0.1]
    """
    import argparse
    import random
    import time
    import sys
    import os
    from datetime import datetime


    from backend.database import Base, SessionLocal, engine

    def init_db():
        Base.metadata.create_all(bind=engine)
    from backend.models import Product
    from backend.models import Transaction
    from backend.models import TransactionItem
    from backend.services import check_retraining_trigger, on_transaction_batch_inserted

    def _simulate_pos_stream_main(argv=None):
        parser = argparse.ArgumentParser(description="Simulate Live POS Stream")
        parser.add_argument("--count", type=int, default=20, help="Number of simulated POS transactions to stream")
        parser.add_argument("--delay", type=float, default=0.05, help="Delay in seconds between transactions")
        parser.add_argument("--restaurant", default="R001", help="Target restaurant ID")
        args = parser.parse_args(argv)

        init_db()
        db = SessionLocal()
        try:
            products = db.query(Product).filter(Product.restaurant_id == args.restaurant).all()
            if not products:
                print("No products found for restaurant R001. Please seed database first.")
                return

            product_ids = [p.product_id for p in products]
            # Realistic pairing affinity weights
            high_affinity_pairs = [
                ("P001", "P005"), # Biryani + Raita
                ("P002", "P006"), # Paneer Tikka + Naan
                ("P004", "P007"), # Samosa + Masala Tea
                ("P003", "P008"), # Chole Bhature + Mango Lassi
                ("P001", "P009"), # Biryani + Gulab Jamun
            ]

            channels = ["dine_in", "dine_in", "takeaway", "online", "online"]

            print(f"\n🚀 Starting POS transaction stream ({args.count} orders for {args.restaurant})...\n")

            for i in range(args.count):
                order_channel = random.choice(channels)
                timestamp = datetime.now()

                # Decide items
                if random.random() < 0.65 and high_affinity_pairs:
                    pair = random.choice(high_affinity_pairs)
                    selected_pids = list(pair)
                    if random.random() < 0.3:
                        selected_pids.append(random.choice(product_ids))
                else:
                    k = random.choices([1, 2, 3, 4], weights=[0.2, 0.5, 0.2, 0.1])[0]
                    selected_pids = random.sample(product_ids, min(k, len(product_ids)))

                # Create Transaction
                tx_id = f"POS-{int(time.time() * 1000)}-{random.randint(100, 999)}"
                tx = Transaction(
                    transaction_id=tx_id,
                    restaurant_id=args.restaurant,
                    customer_id=f"CUST-{random.randint(1000, 9999)}",
                    timestamp=timestamp,
                    order_status="completed",
                    payment_status="paid",
                    channel=order_channel,
                    total_amount=0.0,
                    discount_amount=0.0,
                    created_at=timestamp,
                )
                db.add(tx)

                total = 0.0
                for pid in selected_pids:
                    prod = next((p for p in products if p.product_id == pid), None)
                    price = prod.price if prod else 100.0
                    qty = 1 if random.random() < 0.85 else 2
                    item_total = price * qty
                    total += item_total

                    item = TransactionItem(
                        transaction_id=tx_id,
                        product_id=pid,
                        quantity=qty,
                        unit_price=price,
                        total_price=item_total,
                    )
                    db.add(item)

                tx.total_amount = round(total, 2)
                db.commit()

                print(f"  [Order #{i+1:02d}] {tx_id} | Channel: {order_channel:<8} | Items: {len(selected_pids)} | Total: ₹{total:.2f}")
                time.sleep(args.delay)

            print(f"\n✅ Successfully streamed {args.count} new POS transactions.")

            # Check Retraining Status
            retrain_status = check_retraining_trigger(db, args.restaurant)
            print("\n📊 Retraining Monitor Status:")
            print(f"   Active Model:                 {retrain_status.get('active_model_version', 'None (Rule-Based)')}")
            print(f"   New Transactions Recorded:   {retrain_status.get('new_transactions_since_training', 0)}")
            print(f"   Retraining Trigger Threshold: {retrain_status.get('retrain_threshold', 10000)}")
            print(f"   Remaining to Auto-Retrain:    {retrain_status.get('next_retrain_remaining', 10000)}")
            print(f"   Auto-Retrain Triggered Now:   {retrain_status.get('should_retrain', False)}")

        finally:
            db.close()
    return _simulate_pos_stream_main(argv)


def train_model(argv=None):
    """Run the existing model training CLI with its usual arguments."""
    #!/usr/bin/env python3
    """
    scripts.py train-model - Standalone CLI tool to evaluate and train combo regression models.
    Usage:
        python scripts.py train-model [--restaurant R001] [--force] [--trigger MANUAL]
    """
    import argparse
    import sys
    import os

    # Ensure backend package can be imported

    from backend.database import Base, SessionLocal, engine

    def init_db():
        Base.metadata.create_all(bind=engine)
    from backend.services import train_combo_model_pipeline
    from backend.services import evaluate_restaurant_data_sufficiency
    from backend.services import get_active_model_record

    def _train_model_main(argv=None):
        parser = argparse.ArgumentParser(description="Train Restaurant Combo Machine Learning Model")
        parser.add_argument("--restaurant", default="R001", help="Restaurant ID (default: R001)")
        parser.add_argument("--trigger", default="CLI_MANUAL", help="Trigger name (CLI_MANUAL, SCHEDULED, NEW_DATA)")
        parser.add_argument("--force", action="store_true", help="Force training even if borderline data")
        args = parser.parse_args(argv)

        init_db()
        db = SessionLocal()
        try:
            print(f"\n========================================================")
            print(f"RESTAURANT COMBO INTELLIGENCE - ML MODEL TRAINING PIPELINE")
            print(f"Restaurant ID: {args.restaurant}")
            print(f"Trigger:       {args.trigger}")
            print(f"========================================================\n")

            print("1. Checking Data Sufficiency...")
            sufficiency = evaluate_restaurant_data_sufficiency(db, args.restaurant)
            print(f"   Status:            {sufficiency['status']}")
            print(f"   Sufficient for ML: {sufficiency['sufficient_for_ml']}")
            print(f"   Historical Days:   {sufficiency['historical_days']}")
            print(f"   Total Tx Count:    {sufficiency['total_transactions']}")
            print(f"   Valid Tx Count:    {sufficiency['valid_transactions']}")
            print(f"   Valid Baskets:     {sufficiency['valid_baskets']}")
            print(f"   Data Completeness: {sufficiency['data_completeness']}%")
            print(f"   Reason:            {sufficiency['reason']}\n")

            if not sufficiency["sufficient_for_ml"] and not args.force:
                print("❌ Insufficient data to train reliable ML model.")
                print("   The system will remain in RULE_BASED fallback mode (FP-Growth + Profit Engine).")
                print("   Use --force to train anyway.")
                sys.exit(0)

            print("2. Launching Training Pipeline (Feature Engineering -> Chronological Split -> Tree Fit -> Evaluation)...")
            result = train_combo_model_pipeline(db, args.restaurant, trigger=args.trigger, force=args.force)

            print("\n3. Training Result:")
            print(f"   Success:       {result.get('success')}")
            print(f"   Decision:      {result.get('decision', 'N/A')}")
            print(f"   Message:       {result.get('message')}")
            print(f"   Model Version: {result.get('model_version')}")
            if result.get("metrics"):
                m = result["metrics"]
                print(f"   MAE:           {m.get('mae')}")
                print(f"   RMSE:          {m.get('rmse')}")
                print(f"   Precision@10:  {m.get('precision_at_10')}")
                print(f"   R^2:           {m.get('r2')}")

            active = get_active_model_record(db, args.restaurant)
            if active:
                print(f"\n🏆 Currently Active Model in Registry: {active.model_version} ({active.model_type})")
            else:
                print("\nℹ️ No active ML model promoted. Operating in Rule-Based Mode.")

        finally:
            db.close()
    return _train_model_main(argv)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Restaurant Combo Intelligence maintenance commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate-demo-data", help="Generate data/demo_transactions.csv")
    generate_parser.add_argument("--count", type=int, default=1500)
    generate_parser.add_argument("--output", default="data/demo_transactions.csv")
    subparsers.add_parser("seed-database", help="Reset and seed restaurant_intelligence.db")
    subparsers.add_parser("simulate-pos-stream", help="Stream simulated POS orders")
    subparsers.add_parser("train-model", help="Train/evaluate the restaurant combo model")
    args, remainder = parser.parse_known_args(argv)
    if args.command == "generate-demo-data":
        return generate_demo_data(args.count, args.output)
    if args.command == "seed-database":
        if remainder:
            parser.error("seed-database accepts no additional arguments")
        return seed_database()
    if args.command == "simulate-pos-stream":
        return simulate_pos_stream(remainder)
    return train_model(remainder)


if __name__ == "__main__":
    main()
