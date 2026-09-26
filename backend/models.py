from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy import Column, String, Float, Boolean, DateTime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy import Column, String, DateTime
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy import Column, String, Integer, Float, ForeignKey


# --- models/cart.py ---
class Cart(Base):
    __tablename__ = "carts"

    cart_id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id"), nullable=False, index=True)
    customer_id = Column(String(50), nullable=True)
    status = Column(String(20), default="active")  # active, completed, abandoned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    restaurant = relationship("Restaurant")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

# --- models/cart_item.py ---
class CartItem(Base):
    __tablename__ = "cart_items"

    cart_id = Column(String(50), ForeignKey("carts.cart_id"), primary_key=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), primary_key=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

# --- models/combo.py ---
class ComboCandidate(Base):
    __tablename__ = "combo_candidates"

    combo_id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), nullable=False, index=True)
    product_a_id = Column(String(50), nullable=False, index=True)
    product_b_id = Column(String(50), nullable=False, index=True)
    pair_count = Column(Integer, default=0)
    support = Column(Float, default=0.0)
    confidence_a_to_b = Column(Float, default=0.0)
    confidence_b_to_a = Column(Float, default=0.0)
    lift = Column(Float, default=0.0)
    regular_price = Column(Float, default=0.0)
    combo_cost = Column(Float, default=0.0)
    suggested_price = Column(Float, default=0.0)
    combo_profit = Column(Float, default=0.0)
    profit_margin = Column(Float, default=0.0)
    is_active_recommendation = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- models/drift_result.py ---
class DriftResult(Base):
    __tablename__ = "drift_results"

    drift_id = Column(String(50), primary_key=True)
    restaurant_id = Column(String(50), index=True, nullable=False)
    model_version = Column(String(50), nullable=False)
    feature_name = Column(String(100), nullable=False)
    feature_type = Column(String(20), nullable=False)  # numerical, categorical
    method = Column(String(20), nullable=False)  # psi, ks, js_divergence
    reference_period = Column(String(100), nullable=False)
    current_period = Column(String(100), nullable=False)
    reference_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    drift_score = Column(Float, nullable=False)
    p_value = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # HEALTHY, WARNING, CRITICAL
    created_at = Column(DateTime, default=datetime.utcnow)

# --- models/inventory.py ---
class Inventory(Base):
    __tablename__ = "inventory"

    product_id = Column(String(50), ForeignKey("products.product_id"), primary_key=True)
    current_stock = Column(Integer, default=100)
    minimum_stock = Column(Integer, default=20)
    is_available = Column(Boolean, default=True)
    last_restocked_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="inventory")

# --- models/model_performance.py ---
class ModelPerformanceRecord(Base):
    __tablename__ = "model_performance_records"

    performance_id = Column(String(50), primary_key=True)
    restaurant_id = Column(String(50), index=True, nullable=False)
    model_version = Column(String(50), nullable=False)
    evaluation_period_start = Column(DateTime, nullable=False)
    evaluation_period_end = Column(DateTime, nullable=False)
    sample_size = Column(Integer, nullable=False)
    mae = Column(Float, nullable=False)
    rmse = Column(Float, nullable=False)
    mape = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    degradation_pct = Column(Float, default=0.0)
    status = Column(String(20), default="HEALTHY")
    created_at = Column(DateTime, default=datetime.utcnow)

# --- models/model_registry.py ---
class ModelRegistry(Base):
    __tablename__ = "model_registry"

    model_id = Column(String(100), primary_key=True, index=True)
    restaurant_id = Column(String(50), nullable=False, index=True)
    model_version = Column(String(20), nullable=False, index=True)
    model_type = Column(String(100), default="XGBoostRegressor")
    target = Column(String(100), default="future_combo_purchase_count_7d")
    
    training_start_date = Column(DateTime, nullable=True)
    training_end_date = Column(DateTime, nullable=True)
    validation_start_date = Column(DateTime, nullable=True)
    validation_end_date = Column(DateTime, nullable=True)
    test_start_date = Column(DateTime, nullable=True)
    test_end_date = Column(DateTime, nullable=True)
    
    training_transactions = Column(Integer, default=0)
    training_samples = Column(Integer, default=0)
    
    # Model evaluation metrics
    mae = Column(Float, default=0.0)
    rmse = Column(Float, default=0.0)
    mape = Column(Float, default=0.0)
    r2 = Column(Float, default=0.0)
    precision_at_5 = Column(Float, default=0.0)
    precision_at_10 = Column(Float, default=0.0)
    
    # Statuses: TRAINING, VALIDATED, ACTIVE, REJECTED, ARCHIVED, FAILED
    status = Column(String(30), default="TRAINING", index=True)
    model_path = Column(String(255), nullable=True)
    feature_snapshot = Column(Text, nullable=True) # JSON snapshot of features & versions
    
    created_at = Column(DateTime, default=datetime.utcnow)
    promoted_at = Column(DateTime, nullable=True)

# --- models/monitoring_alert.py ---
class MonitoringAlert(Base):
    __tablename__ = "monitoring_alerts"

    alert_id = Column(String(50), primary_key=True)
    restaurant_id = Column(String(50), index=True, nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # INFO, WARNING, CRITICAL
    title = Column(String(200), nullable=False)
    message = Column(String(500), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    status = Column(String(20), default="OPEN")  # OPEN, ACKNOWLEDGED, RESOLVED
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    occurrence_count = Column(Integer, default=1)
    model_version = Column(String(50), nullable=True)
    suggested_action = Column(String(300), nullable=False)

# --- models/monitoring_snapshot.py ---
class MonitoringSnapshot(Base):
    __tablename__ = "monitoring_snapshots"

    snapshot_id = Column(String(50), primary_key=True)
    restaurant_id = Column(String(50), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    data_completeness = Column(Float, nullable=False)
    transaction_count = Column(Integer, nullable=False)
    valid_transaction_count = Column(Integer, nullable=False)
    duplicate_rate = Column(Float, default=0.0)
    refund_rate = Column(Float, default=0.0)
    multi_item_baskets = Column(Integer, default=0)
    unique_products = Column(Integer, default=0)

# --- models/product.py ---
class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id"), nullable=False, index=True)
    product_name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    selling_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    restaurant = relationship("Restaurant", back_populates="products")
    inventory = relationship("Inventory", uselist=False, back_populates="product")
    transaction_items = relationship("TransactionItem", back_populates="product")

# --- models/promotion.py ---
class Promotion(Base):
    __tablename__ = "promotions"

    promotion_id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    discount_percentage = Column(Float, default=0.0)
    fixed_discount = Column(Float, default=0.0)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

# --- models/recommendation_event.py ---
class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

    event_id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id"), nullable=False, index=True)
    customer_id = Column(String(50), nullable=True)
    cart_id = Column(String(50), nullable=True, index=True)
    recommendation_id = Column(String(50), nullable=True)
    product_id = Column(String(50), nullable=True) # Source or anchor product in cart
    recommended_product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    shown = Column(Boolean, default=True)
    clicked = Column(Boolean, default=False)
    added_to_cart = Column(Boolean, default=False)
    purchased = Column(Boolean, default=False)
    quantity = Column(Integer, default=1)
    price_at_event = Column(Float, default=0.0)
    model_version = Column(String(50), nullable=True)
    recommendation_mode = Column(String(20), default="ml")  # "ml" or "rule_based"

    restaurant = relationship("Restaurant")
    recommended_product = relationship("Product", foreign_keys=[recommended_product_id])

# --- models/recommendation_metric.py ---
class RecommendationMetricRecord(Base):
    __tablename__ = "recommendation_metric_records"

    metric_id = Column(String(50), primary_key=True)
    restaurant_id = Column(String(50), index=True, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    recommendations_shown = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    added_to_cart = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    add_to_cart_rate = Column(Float, default=0.0)
    purchase_conversion = Column(Float, default=0.0)
    coverage = Column(Float, default=0.0)
    fallback_rate = Column(Float, default=0.0)
    no_candidate_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- models/restaurant.py ---
class Restaurant(Base):
    __tablename__ = "restaurants"

    restaurant_id = Column(String(50), primary_key=True, index=True)
    restaurant_name = Column(String(150), nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata")
    currency = Column(String(10), default="INR")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    transactions = relationship("Transaction", back_populates="restaurant")
    products = relationship("Product", back_populates="restaurant")

# --- models/retraining_request.py ---
class RetrainingRequestRecord(Base):
    __tablename__ = "retraining_requests"

    request_id = Column(String(50), primary_key=True)
    restaurant_id = Column(String(50), index=True, nullable=False)
    reason = Column(String(255), nullable=False)
    trigger_type = Column(String(50), nullable=False)  # DATA_DRIFT, MODEL_DEGRADATION, etc.
    trigger_value = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    result = Column(String(500), nullable=True)
    new_model_version = Column(String(50), nullable=True)

# --- models/training_job.py ---
class TrainingJob(Base):
    __tablename__ = "training_jobs"

    job_id = Column(String(100), primary_key=True, index=True)
    restaurant_id = Column(String(50), nullable=False, index=True)
    status = Column(String(30), default="QUEUED", index=True) # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    trigger = Column(String(50), default="MANUAL")           # INITIAL_TRAINING, NEW_DATA_THRESHOLD, SCHEDULED, MANUAL
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    samples = Column(Integer, default=0)
    model_version = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- models/transaction.py ---
class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id"), nullable=False, index=True)
    customer_id = Column(String(50), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    order_status = Column(String(30), default="completed", index=True)  # completed, cancelled, refunded
    payment_status = Column(String(30), default="paid")                  # paid, pending, failed
    channel = Column(String(30), default="dine_in", index=True)          # dine_in, takeaway, delivery, online
    total_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    restaurant = relationship("Restaurant", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction", cascade="all, delete-orphan")

# --- models/transaction_item.py ---
class TransactionItem(Base):
    __tablename__ = "transaction_items"

    transaction_id = Column(String(50), ForeignKey("transactions.transaction_id"), primary_key=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), primary_key=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    net_price = Column(Float, nullable=False)

    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product", back_populates="transaction_items")

__all__ = ['Cart', 'CartItem', 'ComboCandidate', 'DriftResult', 'Inventory', 'ModelPerformanceRecord', 'ModelRegistry', 'MonitoringAlert', 'MonitoringSnapshot', 'Product', 'Promotion', 'RecommendationEvent', 'RecommendationMetricRecord', 'Restaurant', 'RetrainingRequestRecord', 'TrainingJob', 'Transaction', 'TransactionItem']
