from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from typing import Optional, List
from typing import Optional, Dict, Any, List
from typing import Optional


# --- schemas/cart.py ---
class CartItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1)
    unit_price: Optional[float] = None

class CartItemResponse(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class CartCreate(BaseModel):
    restaurant_id: str
    customer_id: Optional[str] = None
    items: Optional[List[CartItemCreate]] = None

class CartResponse(BaseModel):
    cart_id: str
    restaurant_id: str
    customer_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[CartItemResponse]
    total_amount: float

# --- schemas/analytics.py ---
class AssociationRule(BaseModel):
    antecedent_id: str
    antecedent_name: str
    consequent_id: str
    consequent_name: str
    support: float
    confidence: float
    lift: float
    pair_count: int

class ValidationCheck(BaseModel):
    name: str
    status: str  # PASS, WARN, FAIL
    details: str
    metric: Optional[float] = None

class DataQualityReport(BaseModel):
    total_transactions: int
    valid_completed_transactions: int
    cancelled_transactions: int
    refunded_transactions: int
    invalid_or_orphan_items: int
    completeness_rate_pct: float
    checks: List[ValidationCheck]

class DashboardSummaryResponse(BaseModel):
    total_orders: int
    valid_baskets: int
    total_revenue: float
    total_cost: float
    total_profit: float
    avg_margin: float
    top_product: Optional[Dict[str, Any]] = None
    top_combo: Optional[Dict[str, Any]] = None
    active_algorithm: str = "FP-Growth"
    date_filter: str
    channel_filter: str

# --- schemas/combo.py ---
class ComboPriceUpdate(BaseModel):
    price: float = Field(..., gt=0)

class ComboCandidateResponse(BaseModel):
    combo_id: str
    product_a_id: str
    product_a_name: str
    product_a_price: float
    product_a_cost: float
    product_a_stock: int
    product_b_id: str
    product_b_name: str
    product_b_price: float
    product_b_cost: float
    product_b_stock: int
    pair_transaction_count: int
    total_valid_transactions: int
    support: float
    confidence_a_to_b: float
    confidence_b_to_a: float
    lift: float
    regular_sum_price: float
    combo_cost: float
    normal_profit: float
    suggested_combo_price: float
    customer_savings: float
    combo_profit: float
    profit_difference: float
    combo_margin: float
    stock_status: str
    is_candidate_combo: bool
    business_rule_passed: bool
    explanation: str
    recommendation_mode: str = "Rule-Based Recommendation"
    model_version: Optional[str] = None
    predicted_future_combo_purchases_7d: Optional[int] = None
    estimated_gross_profit_7d: Optional[float] = None
    ranking_score: float = 0.0

# --- schemas/model.py ---
class ModelEvaluationMetrics(BaseModel):
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    r2: Optional[float] = None
    precision_at_5: Optional[float] = None
    precision_at_10: Optional[float] = None

class ModelStatusResponse(BaseModel):
    mode: str = Field(..., description="ML_ACTIVE or RULE_BASED")
    status: str = Field(..., description="ACTIVE, TRAINING, INSUFFICIENT_DATA, or READY_FOR_TRAINING")
    model_version: Optional[str] = None
    model_type: Optional[str] = None
    last_trained_at: Optional[str] = None
    training_transactions: int = 0
    new_transactions_since_training: int = 0
    retrain_threshold: int = 10000
    next_retrain_trigger: str = ""
    mae: Optional[float] = None
    rmse: Optional[float] = None
    precision_at_10: Optional[float] = None
    active_job_id: Optional[str] = None
    sufficient_for_ml: bool = False

class ModelMetricsResponse(BaseModel):
    has_active_model: bool
    model_version: Optional[str] = None
    model_type: Optional[str] = None
    target: Optional[str] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    r2: Optional[float] = None
    precision_at_5: Optional[float] = None
    precision_at_10: Optional[float] = None
    training_samples: Optional[int] = None
    training_transactions: Optional[int] = None
    training_date_range: Optional[Dict[str, Optional[str]]] = None
    validation_date_range: Optional[Dict[str, Optional[str]]] = None
    test_date_range: Optional[Dict[str, Optional[str]]] = None
    message: Optional[str] = None

class DataSufficiencyReport(BaseModel):
    sufficient_for_ml: bool
    total_transactions: int
    valid_transactions: int
    historical_days: int
    valid_baskets: int
    data_completeness: float
    reason: str
    breakdown: Optional[Dict[str, Any]] = None

class ModelHistoryItem(BaseModel):
    model_id: str
    model_version: str
    model_type: str
    status: str
    mae: Optional[float] = None
    rmse: Optional[float] = None
    precision_at_10: Optional[float] = None
    training_transactions: int = 0
    promoted_at: Optional[datetime] = None
    created_at: datetime
    can_rollback: bool = False

class TrainTriggerRequest(BaseModel):
    trigger: str = Field("MANUAL", description="MANUAL, NEW_DATA_THRESHOLD, or SCHEDULED")
    force: bool = False

class RollbackRequest(BaseModel):
    target_version: str
    reason: Optional[str] = "Performance rollback requested by restaurant manager"

# --- schemas/product.py ---
class ProductBase(BaseModel):
    product_name: str
    category: str
    selling_price: float = Field(..., gt=0)
    cost_price: float = Field(..., gt=0)
    is_active: bool = True

class ProductCreate(ProductBase):
    product_id: str
    restaurant_id: str

class ProductResponse(ProductBase):
    product_id: str
    restaurant_id: str
    profit_per_unit: float
    profit_margin: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductSalesStat(BaseModel):
    product_id: str
    product_name: str
    category: str
    selling_price: float
    cost_price: float
    total_quantity_sold: int
    transaction_count: int
    total_revenue: float
    total_profit: float
    profit_margin: float
    current_stock: int
    stock_status: str

# --- schemas/recommendation.py ---
class RecommendationRequest(BaseModel):
    restaurant_id: str
    cart_id: Optional[str] = None
    items: List[CartItemCreate] = Field(default_factory=list)
    customer_id: Optional[str] = None
    limit: int = Field(5, ge=1, le=20)

class CustomerRecommendationItem(BaseModel):
    product_id: str
    product_name: str
    price: float
    reason: str
    category: Optional[str] = None
    score: Optional[float] = None

class CustomerRecommendationResponse(BaseModel):
    restaurant_id: str
    cart_id: Optional[str] = None
    recommendations: List[CustomerRecommendationItem]

class ManagerRecommendationItem(BaseModel):
    product_id: str
    product_name: str
    source_product_ids: List[str]
    score: float
    confidence: float
    lift: float
    pair_transaction_count: int
    current_stock: int
    available: bool
    price: float
    cost: float
    combo_profit: float
    profit_margin: float
    ml_prediction: Optional[float] = None
    recommendation_mode: str
    model_version: Optional[str] = None
    reason: str
    explanation: str

class RecommendationResponse(BaseModel):
    restaurant_id: str
    cart_id: Optional[str] = None
    recommendation_mode: str # "ml", "rule_based", or "insufficient_data"
    model_version: Optional[str] = None
    latency_ms: float
    recommendations: List[ManagerRecommendationItem]
    trace: Optional[Dict[str, Any]] = None

class RecommendationEventCreate(BaseModel):
    restaurant_id: str
    event_id: Optional[str] = None
    customer_id: Optional[str] = None
    cart_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    product_id: Optional[str] = None
    recommended_product_id: str
    shown: bool = True
    clicked: bool = False
    added_to_cart: bool = False
    purchased: bool = False
    quantity: int = 1
    price_at_event: float = 0.0
    model_version: Optional[str] = None
    recommendation_mode: str = "ml"

class RecommendationMetricsResponse(BaseModel):
    restaurant_id: str
    shown_count: int
    click_count: int
    add_to_cart_count: int
    purchase_count: int
    ctr: float
    add_to_cart_rate: float
    purchase_conversion_rate: float
    recent_events_count: int

# --- schemas/transaction.py ---
class TransactionItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)
    unit_price: Optional[float] = None
    discount_amount: float = 0.0

class TransactionCreate(BaseModel):
    restaurant_id: str = "R001"
    customer_id: Optional[str] = None
    channel: str = "dine_in"
    items: List[TransactionItemCreate]

class TransactionItemResponse(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    discount_amount: float
    net_price: float

class TransactionResponse(BaseModel):
    transaction_id: str
    restaurant_id: str
    customer_id: Optional[str] = None
    timestamp: datetime
    order_status: str
    payment_status: str
    channel: str
    total_amount: float
    discount_amount: float
    items: List[TransactionItemResponse]

    class Config:
        from_attributes = True

__all__ = ['CartItemCreate', 'CartItemResponse', 'CartCreate', 'CartResponse', 'AssociationRule', 'ValidationCheck', 'DataQualityReport', 'DashboardSummaryResponse', 'ComboPriceUpdate', 'ComboCandidateResponse', 'ModelEvaluationMetrics', 'ModelStatusResponse', 'ModelMetricsResponse', 'DataSufficiencyReport', 'ModelHistoryItem', 'TrainTriggerRequest', 'RollbackRequest', 'ProductBase', 'ProductCreate', 'ProductResponse', 'ProductSalesStat', 'RecommendationRequest', 'CustomerRecommendationItem', 'CustomerRecommendationResponse', 'ManagerRecommendationItem', 'RecommendationResponse', 'RecommendationEventCreate', 'RecommendationMetricsResponse', 'TransactionItemCreate', 'TransactionCreate', 'TransactionItemResponse', 'TransactionResponse']
