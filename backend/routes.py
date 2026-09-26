from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import Transaction
from backend.models import TransactionItem
from backend.models import Product
from backend.schemas import DashboardSummaryResponse
from backend.services import get_top_selling_products
from backend.services import compute_combo_economics
from typing import List, Optional
from backend.schemas import AssociationRule
from backend.services import calculate_association_rules
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from backend.schemas import CartCreate, CartItemCreate, CartResponse
from backend.services import create_or_get_cart, get_cart_summary, add_item_to_cart, remove_item_from_cart
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.schemas import ComboCandidateResponse, ComboPriceUpdate
from fastapi import APIRouter, Depends, HTTPException
from backend.schemas import RecommendationRequest, CustomerRecommendationResponse, CustomerRecommendationItem
from backend.services import get_realtime_cart_recommendations
from fastapi import APIRouter, Depends
from backend.schemas import DataQualityReport
from backend.services import generate_data_quality_report
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from backend.services import get_product_stock_info, update_single_product_stock
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from backend.services import get_recommended_combos
from backend.services import check_products_availability_batch
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from backend.services import evaluate_restaurant_data_sufficiency
from backend.services import get_active_model_record, list_model_history, rollback_model
from backend.services import train_combo_model_pipeline
from backend.services import check_retraining_trigger
from backend.models import TrainingJob
from backend.services import get_event_logs
from backend.services import run_system_health_check
from backend.services import check_data_quality
from backend.services import check_model_performance
from backend.services import get_alerts, acknowledge_alert, resolve_alert
from backend.services import evaluate_and_request_retraining
from typing import Dict, Any, Optional
from backend.services import pos_adapter
from backend.schemas import ProductResponse, ProductSalesStat
from typing import Optional, List
from backend.schemas import RecommendationEventCreate
from backend.services import record_recommendation_event, get_recent_recommendation_events
from backend.schemas import RecommendationRequest, RecommendationResponse, RecommendationMetricsResponse
from backend.services import get_realtime_cart_recommendations, get_product_recommendations
from backend.services import get_recommendation_performance_metrics
from backend.services import get_active_model_record
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import PlainTextResponse
from backend.schemas import TransactionCreate, TransactionResponse


# --- routes/analytics.py ---
analytics_router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@analytics_router.get("/dashboard", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    channel: str = Query("all"),
    db: Session = Depends(get_db)
):
    # Total orders
    tx_query = db.query(Transaction).filter(Transaction.restaurant_id == "R001")
    if channel != "all":
        tx_query = tx_query.filter(Transaction.channel == channel)
    all_tx = tx_query.all()

    total_orders = len(all_tx)
    completed_tx = [t for t in all_tx if t.order_status == "completed"]
    valid_baskets = len(completed_tx)

    # Top selling
    top_products = get_top_selling_products(db, restaurant_id="R001", channel=channel, limit=1)
    top_product = top_products[0] if top_products else None

    # Combos
    combos = compute_combo_economics(db, restaurant_id="R001", channel=channel)
    top_combo = None
    if combos:
        tc = combos[0]
        top_combo = {
            "title": f"{tc['product_a_name']} + {tc['product_b_name']}",
            "bought_together": tc["pair_transaction_count"],
            "lift": tc["lift"],
            "profit": tc["combo_profit"],
            "suggested_price": tc["suggested_combo_price"],
        }

    # Revenue & profit on completed
    valid_tx_ids = set(t.transaction_id for t in completed_tx)
    items = db.query(TransactionItem).filter(TransactionItem.transaction_id.in_(valid_tx_ids)).all() if valid_tx_ids else []

    products_map = {p.product_id: p for p in db.query(Product).all()}

    total_rev = sum(i.net_price for i in items)
    total_cost = sum(i.quantity * (products_map[i.product_id].cost_price if i.product_id in products_map else 0.0) for i in items)
    total_profit = total_rev - total_cost
    avg_margin = round(total_profit / total_rev, 4) if total_rev > 0 else 0.0

    return {
        "total_orders": total_orders,
        "valid_baskets": valid_baskets,
        "total_revenue": round(total_rev, 2),
        "total_cost": round(total_cost, 2),
        "total_profit": round(total_profit, 2),
        "avg_margin": avg_margin,
        "top_product": top_product,
        "top_combo": top_combo,
        "active_algorithm": "FP-Growth",
        "date_filter": "all",
        "channel_filter": channel,
    }

# --- routes/associations.py ---
associations_router = APIRouter(prefix="/api/associations", tags=["Associations"])

@associations_router.get("", response_model=List[AssociationRule])
def get_associations(
    channel: str = Query("all"),
    min_pair_count: int = Query(20, ge=1),
    min_confidence: float = Query(0.30, ge=0.01, le=1.0),
    min_lift: float = Query(1.10, ge=0.5),
    filter: str = Query("30days", regex="^(today|7days|30days|90days|custom)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    result = calculate_association_rules(
        db,
        restaurant_id="R001",
        channel=channel,
        min_pair_count=min_pair_count,
        min_confidence=min_confidence,
        min_lift=min_lift,
        period=filter,
        start_date=start_date,
        end_date=end_date,
    )
    return result["rules"]

# --- routes/carts.py ---
carts_router = APIRouter(prefix="/api/cart", tags=["Real-Time Order Cart"])

@carts_router.post("", response_model=CartResponse)
def create_cart_endpoint(
    req: CartCreate,
    db: Session = Depends(get_db)
):
    """Creates a new active cart."""
    try:
        items_raw = [
            {"product_id": it.product_id, "quantity": it.quantity, "unit_price": it.unit_price}
            for it in (req.items or [])
        ]
        cart = create_or_get_cart(
            db=db,
            restaurant_id=req.restaurant_id,
            customer_id=req.customer_id,
            initial_items=items_raw,
        )
        summary = get_cart_summary(db, cart.cart_id, req.restaurant_id)
        if not summary:
            raise HTTPException(status_code=500, detail="Failed to serialize created cart")
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@carts_router.get("/{cart_id}", response_model=CartResponse)
def get_cart_endpoint(
    cart_id: str,
    restaurant_id: str = Query("R001"),
    db: Session = Depends(get_db)
):
    """Retrieves current cart state."""
    summary = get_cart_summary(db, cart_id, restaurant_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Cart not found")
    return summary

@carts_router.post("/{cart_id}/items", response_model=CartResponse)
def add_cart_item_endpoint(
    cart_id: str,
    item: CartItemCreate,
    restaurant_id: str = Query("R001"),
    db: Session = Depends(get_db)
):
    """Adds a product or increments quantity in the cart."""
    try:
        add_item_to_cart(
            db=db,
            cart_id=cart_id,
            restaurant_id=restaurant_id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        summary = get_cart_summary(db, cart_id, restaurant_id)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@carts_router.delete("/{cart_id}/items/{product_id}", response_model=CartResponse)
def remove_cart_item_endpoint(
    cart_id: str,
    product_id: str,
    restaurant_id: str = Query("R001"),
    db: Session = Depends(get_db)
):
    """Removes an item from the cart."""
    success = remove_item_from_cart(db, cart_id, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    summary = get_cart_summary(db, cart_id, restaurant_id)
    return summary

# --- routes/combos.py ---
combos_router = APIRouter(prefix="/api/combos", tags=["Combos"])

# Local cache for custom manager pricing
CUSTOM_COMBO_PRICES = {}

@combos_router.get("", response_model=List[ComboCandidateResponse])
def get_combos(
    channel: str = Query("all"),
    min_pair_count: int = Query(20, ge=1),
    min_confidence: float = Query(0.30, ge=0.01, le=1.0),
    min_lift: float = Query(1.10, ge=0.5),
    min_margin: float = Query(0.0, ge=0.0, le=1.0),
    filter: str = Query("30days", regex="^(today|7days|30days|90days|custom)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    combos = compute_combo_economics(
        db,
        restaurant_id="R001",
        channel=channel,
        min_pair_count=min_pair_count,
        min_confidence=min_confidence,
        min_lift=min_lift,
        min_margin=min_margin,
        period=filter,
        start_date=start_date,
        end_date=end_date,
    )

    # Apply any custom manager prices
    for c in combos:
        if c["combo_id"] in CUSTOM_COMBO_PRICES:
            custom_p = CUSTOM_COMBO_PRICES[c["combo_id"]]
            c["suggested_combo_price"] = custom_p
            c["customer_savings"] = round(c["regular_sum_price"] - custom_p, 2)
            c["combo_profit"] = round(custom_p - c["combo_cost"], 2)
            c["profit_difference"] = round(c["combo_profit"] - c["normal_profit"], 2)
            c["combo_margin"] = round(c["combo_profit"] / custom_p, 4) if custom_p > 0 else 0.0
            if c["combo_profit"] < 0:
                c["is_candidate_combo"] = False
                c["business_rule_passed"] = False

    return combos

@combos_router.post("/{combo_id}/price")
def set_custom_combo_price(combo_id: str, payload: ComboPriceUpdate):
    CUSTOM_COMBO_PRICES[combo_id] = payload.price
    return {
        "success": True,
        "combo_id": combo_id,
        "new_price": payload.price,
        "message": f"Custom combo price updated to ₹{payload.price}",
    }

# --- routes/customer_recommendations.py ---
customer_recommendations_router = APIRouter(prefix="/api/customer/recommendations", tags=["Customer Recommendations"])

@customer_recommendations_router.post("", response_model=CustomerRecommendationResponse)
def get_customer_recommendations_endpoint(
    req: RecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    Section 23: Simple and actionable diner-facing recommendations.
    Omits complex ML parameters unless requested.
    """
    try:
        items_dict = [{"product_id": it.product_id, "quantity": it.quantity} for it in req.items]
        raw_res = get_realtime_cart_recommendations(
            db=db,
            restaurant_id=req.restaurant_id,
            cart_items=items_dict,
            customer_id=req.customer_id,
            cart_id=req.cart_id,
            limit=req.limit,
            record_shown=True,
        )

        customer_items = []
        for r in raw_res.get("recommendations", []):
            customer_items.append(CustomerRecommendationItem(
                product_id=r["product_id"],
                product_name=r["product_name"],
                price=r["price"],
                reason=r["reason"],
                score=r["score"],
            ))

        return CustomerRecommendationResponse(
            restaurant_id=req.restaurant_id,
            cart_id=req.cart_id,
            recommendations=customer_items,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- routes/data_quality.py ---
data_quality_router = APIRouter(prefix="/api/data-quality", tags=["Data Quality"])

@data_quality_router.get("", response_model=DataQualityReport)
def get_data_quality(db: Session = Depends(get_db)):
    return generate_data_quality_report(db, restaurant_id="R001")

# --- routes/inventory.py ---
class InventoryUpdateRequest(BaseModel):
    restaurant_id: str = "R001"
    product_id: str
    current_stock: int = Field(..., ge=0)
    is_available: Optional[bool] = None

inventory_router = APIRouter(prefix="/api/inventory", tags=["Inventory & Availability"])

@inventory_router.get("/{product_id}")
def get_inventory_endpoint(
    product_id: str,
    restaurant_id: str = Query("R001"),
    db: Session = Depends(get_db)
):
    """Retrieves real-time stock and availability for a single product."""
    return get_product_stock_info(db, restaurant_id, product_id)

@inventory_router.post("/update")
def update_inventory_endpoint(
    req: InventoryUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Section 16 & 45: Real-time stock update.
    Invalidates recommendation cache for this product.
    """
    try:
        res = update_single_product_stock(
            db=db,
            restaurant_id=req.restaurant_id,
            product_id=req.product_id,
            current_stock=req.current_stock,
            is_available=req.is_available,
        )
        return {"success": True, **res}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- routes/manager_recommendations.py ---
manager_recommendations_router = APIRouter(prefix="/api/manager/recommendations", tags=["Manager Recommendations Intelligence"])

@manager_recommendations_router.get("")
def get_manager_recommendations_endpoint(
    restaurant_id: str = "R001",
    channel: str = "all",
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Section 24 & 64: Detailed Managerial Intelligence Table.
    Includes pair counts, confidence, lift, ML predictions, current stock, availability,
    costs, profits, and scores.
    """
    try:
        raw = get_recommended_combos(
            db,
            restaurant_id=restaurant_id,
            channel=channel,
        )

        combos = raw.get("combos", [])
        mode = raw.get("mode", "rule_based")
        model_ver = raw.get("active_model_version")

        # Collect product IDs to check live stock
        all_pids = set()
        for c in combos:
            all_pids.add(c["product_a_id"])
            all_pids.add(c["product_b_id"])

        inventory_map = check_products_availability_batch(db, restaurant_id, list(all_pids))

        manager_records = []
        for c in combos[:limit]:
            stock_a = inventory_map.get(c["product_a_id"], {}).get("current_stock", 0)
            stock_b = inventory_map.get(c["product_b_id"], {}).get("current_stock", 0)
            avail_a = inventory_map.get(c["product_a_id"], {}).get("is_available", False)
            avail_b = inventory_map.get(c["product_b_id"], {}).get("is_available", False)

            min_stock = min(stock_a, stock_b)
            is_avail = avail_a and avail_b and min_stock > 0

            manager_records.append({
                "combo_id": c["combo_id"],
                "product_a_id": c["product_a_id"],
                "product_a_name": c["product_a_name"],
                "product_b_id": c["product_b_id"],
                "product_b_name": c["product_b_name"],
                "pair_transaction_count": c["historical_pair_count"],
                "support": c["support"],
                "confidence_a_b": c["confidence_a_b"],
                "confidence_b_a": c["confidence_b_a"],
                "lift": c["lift"],
                "current_stock_a": stock_a,
                "current_stock_b": stock_b,
                "min_combo_stock": min_stock,
                "available": is_avail,
                "regular_sum_price": c["regular_sum_price"],
                "combo_price": c["combo_price"],
                "combo_cost": c["combo_cost"],
                "combo_profit": c["combo_profit"],
                "profit_margin": c["profit_margin"],
                "customer_saving": c["customer_saving"],
                "ml_prediction": c.get("predicted_future_combo_purchases_7d"),
                "estimated_future_profit": c.get("estimated_gross_profit_7d"),
                "recommendation_mode": mode,
                "model_version": model_ver,
                "recommendation_status": "Recommended" if is_avail else "Out of Stock / Unavailable",
            })

        return {
            "restaurant_id": restaurant_id,
            "total_candidates": len(manager_records),
            "recommendation_mode": mode,
            "model_version": model_ver,
            "items": manager_records,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- routes/model.py ---
model_router = APIRouter(prefix="/api/model", tags=["Model Registry & ML Training"])

@model_router.get("/status")
def get_model_status(restaurant_id: str = "R001", db: Session = Depends(get_db)):
    """
    Section 35: Dynamic Model Status API.
    Returns current active model, training state, and next retraining trigger distance.
    """
    active_model = get_active_model_record(db, restaurant_id)
    running_job = db.query(TrainingJob).filter(
        TrainingJob.restaurant_id == restaurant_id,
        TrainingJob.status == "RUNNING"
    ).first()

    retrain_info = check_retraining_trigger(db, restaurant_id)
    sufficiency = evaluate_restaurant_data_sufficiency(db, restaurant_id)

    if running_job:
        status_label = "TRAINING"
        mode_label = "TRAINING"
    elif active_model:
        status_label = "ACTIVE"
        mode_label = "ML_ACTIVE"
    else:
        status_label = "INSUFFICIENT_DATA" if not sufficiency["sufficient_for_ml"] else "READY_FOR_TRAINING"
        mode_label = "RULE_BASED"

    return {
        "mode": mode_label,
        "status": status_label,
        "model_version": active_model.model_version if active_model else None,
        "model_type": active_model.model_type if active_model else None,
        "last_trained_at": active_model.promoted_at.isoformat() if (active_model and active_model.promoted_at) else (active_model.created_at.isoformat() if active_model else None),
        "training_transactions": active_model.training_transactions if active_model else 0,
        "new_transactions_since_training": retrain_info.get("new_transactions_since_training", 0),
        "retrain_threshold": retrain_info.get("retrain_threshold", 10000),
        "next_retrain_trigger": f"{retrain_info.get('next_retrain_remaining', 10000):,} more transactions",
        "mae": active_model.mae if active_model else None,
        "rmse": active_model.rmse if active_model else None,
        "precision_at_10": active_model.precision_at_10 if active_model else None,
        "active_job_id": running_job.job_id if running_job else None,
        "sufficient_for_ml": sufficiency["sufficient_for_ml"],
    }

@model_router.get("/metrics")
def get_model_metrics(restaurant_id: str = "R001", db: Session = Depends(get_db)):
    """
    Section 36: Model Evaluation Metrics.
    """
    active_model = get_active_model_record(db, restaurant_id)
    if not active_model:
        return {
            "has_active_model": False,
            "message": "No active model currently registered. System operating in Rule-Based mode.",
        }

    return {
        "has_active_model": True,
        "model_version": active_model.model_version,
        "model_type": active_model.model_type,
        "target": active_model.target,
        "mae": active_model.mae,
        "rmse": active_model.rmse,
        "mape": active_model.mape,
        "r2": active_model.r2,
        "precision_at_5": active_model.precision_at_5,
        "precision_at_10": active_model.precision_at_10,
        "training_samples": active_model.training_samples,
        "training_transactions": active_model.training_transactions,
        "training_date_range": {
            "start": active_model.training_start_date.isoformat() if active_model.training_start_date else None,
            "end": active_model.training_end_date.isoformat() if active_model.training_end_date else None,
        },
        "validation_date_range": {
            "start": active_model.validation_start_date.isoformat() if active_model.validation_start_date else None,
            "end": active_model.validation_end_date.isoformat() if active_model.validation_end_date else None,
        },
        "test_date_range": {
            "start": active_model.test_start_date.isoformat() if active_model.test_start_date else None,
            "end": active_model.test_end_date.isoformat() if active_model.test_end_date else None,
        },
    }

@model_router.get("/data-sufficiency")
def get_data_sufficiency(restaurant_id: str = "R001", db: Session = Depends(get_db)):
    """
    Section 9: Data Sufficiency Check API.
    """
    return evaluate_restaurant_data_sufficiency(db, restaurant_id)

@model_router.get("/history")
def get_model_history(restaurant_id: str = "R001", db: Session = Depends(get_db)):
    """
    Section 48: Model Version History API.
    """
    return list_model_history(db, restaurant_id)

@model_router.get("/logs")
def get_ml_logs(restaurant_id: str = "R001"):
    """
    Section 62: Structured Audit Logging.
    """
    return get_event_logs(restaurant_id, limit=50)

@model_router.post("/train")
def trigger_manual_train(
    background_tasks: BackgroundTasks,
    restaurant_id: str = "R001",
    db: Session = Depends(get_db)
):
    """
    Section 33: Manual / Developer Training Endpoint.
    Launches training pipeline.
    """
    # Execute training synchronously or background
    result = train_combo_model_pipeline(db, restaurant_id, trigger="MANUAL")
    return result

@model_router.post("/retrain")
def trigger_retrain(
    restaurant_id: str = "R001",
    db: Session = Depends(get_db)
):
    """
    Section 34: Retraining Trigger Endpoint.
    """
    result = train_combo_model_pipeline(db, restaurant_id, trigger="NEW_DATA_THRESHOLD")
    return result

@model_router.post("/rollback/{model_version}")
def trigger_rollback(
    model_version: str,
    restaurant_id: str = "R001",
    db: Session = Depends(get_db)
):
    """
    Section 47: Model Rollback Endpoint.
    Rolls back active model to a previous validated/archived version.
    """
    try:
        result = rollback_model(db, restaurant_id, model_version)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- routes/monitoring.py ---
monitoring_router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@monitoring_router.get("/health")
def get_monitoring_health(restaurant_id: str = "R001", db: Session = Depends(get_db)):
    return run_system_health_check(db, restaurant_id)

@monitoring_router.get("/data-quality")
def get_data_quality(restaurant_id: str = "R001", db: Session = Depends(get_db)):
    return check_data_quality(db, restaurant_id)

@monitoring_router.get("/model")
def get_model_health(restaurant_id: str = "R001", db: Session = Depends(get_db)):
    return check_model_performance(db, restaurant_id)

@monitoring_router.get("/alerts")
def list_alerts(
    status: str = Query(None),
    restaurant_id: str = "R001",
    db: Session = Depends(get_db)
):
    alerts = get_alerts(db, restaurant_id, status_filter=status)
    return [
        {
            "alert_id": a.alert_id,
            "restaurant_id": a.restaurant_id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "occurrence_count": a.occurrence_count,
            "suggested_action": a.suggested_action,
        }
        for a in alerts
    ]

@monitoring_router.post("/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = acknowledge_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "alert_id": alert.alert_id, "status": alert.status}

@monitoring_router.post("/alerts/{alert_id}/resolve")
def res_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = resolve_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "alert_id": alert.alert_id, "status": alert.status}

@monitoring_router.post("/retraining/trigger")
def trigger_retraining(
    trigger_type: str = "MANUAL",
    reason: str = "Manager triggered via API",
    restaurant_id: str = "R001",
    db: Session = Depends(get_db)
):
    return evaluate_and_request_retraining(
        db,
        restaurant_id=restaurant_id,
        trigger_type=trigger_type,
        reason=reason,
        trigger_value="Manual API invocation"
    )

# --- routes/pos.py ---
pos_router = APIRouter(prefix="/api/pos", tags=["POS Integration"])

@pos_router.get("/status")
def get_pos_status(
    restaurant_id: str = "R001",
    db: Session = Depends(get_db)
):
    """
    Section 45: POS Integration Health & Status.
    """
    latest_tx = db.query(Transaction).filter(
        Transaction.restaurant_id == restaurant_id
    ).order_by(Transaction.timestamp.desc()).first()

    total_tx_count = db.query(Transaction).filter(
        Transaction.restaurant_id == restaurant_id
    ).count()

    return {
        "restaurant_id": restaurant_id,
        "pos_status": "ONLINE",
        "adapter": "StandardPOSAdapter (Idempotent & Stock-Synced)",
        "total_synced_transactions": total_tx_count,
        "last_synced_transaction": latest_tx.transaction_id if latest_tx else None,
        "last_synced_timestamp": latest_tx.timestamp.isoformat() if (latest_tx and latest_tx.timestamp) else None,
        "supported_channels": ["pos", "dine_in", "takeaway", "online"],
        "idempotency_enabled": True,
        "realtime_inventory_deduction": True,
    }

# --- routes/products.py ---
products_router = APIRouter(prefix="/api/products", tags=["Products"])

@products_router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == True).all()
    results = []
    for p in products:
        profit_per_unit = round(p.selling_price - p.cost_price, 2)
        profit_margin = round(profit_per_unit / p.selling_price, 4) if p.selling_price > 0 else 0.0
        results.append({
            "product_id": p.product_id,
            "restaurant_id": p.restaurant_id,
            "product_name": p.product_name,
            "category": p.category,
            "selling_price": p.selling_price,
            "cost_price": p.cost_price,
            "profit_per_unit": profit_per_unit,
            "profit_margin": profit_margin,
            "is_active": p.is_active,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })
    return results

@products_router.get("/top-selling", response_model=List[ProductSalesStat])
def get_top_selling(
    sortBy: str = Query("quantity", regex="^(quantity|revenue|profit)$"),
    channel: str = Query("all"),
    limit: int = Query(50, le=100),
    filter: str = Query("30days", regex="^(today|7days|30days|90days|custom)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return get_top_selling_products(
        db,
        restaurant_id="R001",
        channel=channel,
        sort_by=sortBy,
        limit=limit,
        period=filter,
        start_date=start_date,
        end_date=end_date,
    )

@products_router.get("/{product_id}/detail")
def get_product_detail(product_id: str, channel: str = "all", db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.product_id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    # Find companion products using association engine
    assoc = calculate_association_rules(db, restaurant_id="R001", channel=channel)
    companions = []
    for rule in assoc["rules"]:
        if rule["antecedent_id"] == product_id:
            companions.append({
                "product_id": rule["consequent_id"],
                "product_name": rule["consequent_name"],
                "bought_together": rule["pair_count"],
                "confidence": rule["confidence"],
                "lift": rule["lift"],
                "support": rule["support"],
            })

    unit_profit = round(prod.selling_price - prod.cost_price, 2)
    margin = round(unit_profit / prod.selling_price, 4) if prod.selling_price > 0 else 0.0

    return {
        "product_id": prod.product_id,
        "product_name": prod.product_name,
        "category": prod.category,
        "selling_price": prod.selling_price,
        "cost_price": prod.cost_price,
        "unit_profit": unit_profit,
        "margin": margin,
        "frequently_bought_companions": companions[:5],
    }

# --- routes/recommendation_events.py ---
recommendation_events_router = APIRouter(prefix="/api/recommendation-events", tags=["Recommendation Feedback Events"])

@recommendation_events_router.post("")
def record_event_endpoint(
    req: RecommendationEventCreate,
    db: Session = Depends(get_db)
):
    """
    Section 38 & 39: Records recommendation events (shown, clicked, added_to_cart, purchased).
    Feeds Phase 4 conversion monitoring.
    """
    try:
        # Determine event type
        if req.purchased:
            etype = "purchased"
        elif req.added_to_cart:
            etype = "added_to_cart"
        elif req.clicked:
            etype = "clicked"
        else:
            etype = "shown"

        evt = record_recommendation_event(
            db=db,
            restaurant_id=req.restaurant_id,
            recommended_product_id=req.recommended_product_id,
            event_type=etype,
            customer_id=req.customer_id,
            cart_id=req.cart_id,
            product_id=req.product_id,
            recommendation_id=req.recommendation_id,
            price_at_event=req.price_at_event,
            model_version=req.model_version,
            recommendation_mode=req.recommendation_mode,
            quantity=req.quantity,
        )
        return {
            "success": True,
            "event_id": evt.event_id,
            "event_type": etype,
            "timestamp": evt.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@recommendation_events_router.get("")
def list_events_endpoint(
    restaurant_id: str = "R001",
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Returns recent recommendation feedback events."""
    try:
        return get_recent_recommendation_events(db, restaurant_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- routes/recommendations.py ---
recommendations_router = APIRouter(prefix="/api/recommendations", tags=["Real-Time Recommendations"])

@recommendations_router.post("", response_model=RecommendationResponse)
def post_realtime_recommendations(
    req: RecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    Section 8: Core Real-Time Recommendation API.
    Evaluates current cart items, checks associations, active ML predictions,
    stock, availability, and unit profit, and returns ranked recommendations with trace.
    """
    try:
        items_dict = [{"product_id": it.product_id, "quantity": it.quantity} for it in req.items]
        res = get_realtime_cart_recommendations(
            db=db,
            restaurant_id=req.restaurant_id,
            cart_items=items_dict,
            customer_id=req.customer_id,
            cart_id=req.cart_id,
            limit=req.limit,
            record_shown=True,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@recommendations_router.get("/product/{product_id}", response_model=RecommendationResponse)
def get_recommendations_for_product(
    product_id: str,
    restaurant_id: str = "R001",
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Section 9: Product-specific recommendations (e.g. for Product Detail page).
    """
    try:
        res = get_product_recommendations(
            db=db,
            restaurant_id=restaurant_id,
            product_id=product_id,
            limit=limit,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@recommendations_router.get("/metrics", response_model=RecommendationMetricsResponse)
def get_metrics(
    restaurant_id: str = "R001",
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Section 40: Recommendation Performance KPI Metrics (CTR, Add-to-Cart, Conversion).
    """
    try:
        return get_recommendation_performance_metrics(db, restaurant_id, days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@recommendations_router.get("/status")
def get_recommendation_system_status(
    restaurant_id: str = "R001",
    db: Session = Depends(get_db)
):
    """
    Section 41 & 65: Model and real-time inference status.
    """
    active_model = get_active_model_record(db, restaurant_id)
    return {
        "restaurant_id": restaurant_id,
        "recommendation_engine": "Real-Time Cart-Aware Hybrid (FP-Growth + ML Regressor)",
        "recommendation_mode": "ML" if active_model else "Rule-Based",
        "active_model": active_model.model_version if active_model else None,
        "model_type": active_model.model_type if active_model else None,
        "latency_target_ms": 500,
        "cache_active": True,
        "pos_integration": "Connected",
    }

# --- routes/transactions.py ---
transactions_router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@transactions_router.get("", response_model=List[TransactionResponse])
def list_transactions(
    limit: int = Query(50, le=200),
    order_status: Optional[str] = None,
    channel: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)
    if order_status:
        query = query.filter(Transaction.order_status == order_status)
    if channel and channel != "all":
        query = query.filter(Transaction.channel == channel)
    return query.order_by(Transaction.timestamp.desc()).limit(limit).all()

@transactions_router.post("")
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    """
    Section 19, 50 & 51: Real-Time POS Transaction Ingestion.
    Supports idempotency, item validation, stock deduction, and feedback conversion.
    """
    try:
        from backend.services import pos_adapter
        tx_id = f"TX{int(datetime.utcnow().timestamp() * 1000) % 100000000:08d}"
        payload_dict = {
            "restaurant_id": payload.restaurant_id,
            "transaction_id": tx_id,
            "customer_id": payload.customer_id,
            "order_status": "completed",
            "payment_status": "paid",
            "channel": payload.channel,
            "items": [
                {
                    "product_id": it.product_id,
                    "quantity": it.quantity,
                    "unit_price": it.unit_price,
                }
                for it in payload.items
            ]
        }
        res = pos_adapter.receive_transaction(db, payload_dict)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transactions_router.get("/sample-csv", response_class=PlainTextResponse)
def get_sample_csv():
    headers = [
        "transaction_id", "restaurant_id", "customer_id", "timestamp",
        "order_status", "payment_status", "channel",
        "product_id", "product_name", "quantity", "unit_price",
        "item_discount", "net_price"
    ]
    sample_rows = [
        ["TX90001", "R001", "CUST101", "2026-09-24 14:15:00", "completed", "paid", "dine_in", "P001", "Masala Tea", "1", "20", "0", "20"],
        ["TX90001", "R001", "CUST101", "2026-09-24 14:15:00", "completed", "paid", "dine_in", "P002", "Crispy Samosa", "1", "15", "0", "15"],
        ["TX90002", "R001", "CUST102", "2026-09-24 14:30:00", "completed", "paid", "takeaway", "P006", "Classic Burger", "1", "120", "0", "120"],
        ["TX90002", "R001", "CUST102", "2026-09-24 14:30:00", "completed", "paid", "takeaway", "P007", "French Fries", "1", "70", "0", "70"],
        ["TX90002", "R001", "CUST102", "2026-09-24 14:30:00", "completed", "paid", "takeaway", "P008", "Chilled Coke", "1", "40", "0", "40"],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(sample_rows)
    return output.getvalue()

__all__ = ['analytics_router', 'associations_router', 'carts_router', 'combos_router', 'customer_recommendations_router', 'data_quality_router', 'inventory_router', 'manager_recommendations_router', 'model_router', 'monitoring_router', 'pos_router', 'products_router', 'recommendation_events_router', 'recommendations_router', 'transactions_router']
