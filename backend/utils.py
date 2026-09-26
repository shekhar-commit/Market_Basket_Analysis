from enum import Enum


# --- utils/constants.py ---
class OrderChannel(str, Enum):
    ALL = "all"
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"
    DELIVERY = "delivery"
    ONLINE = "online"

class OrderStatus(str, Enum):
    ALL = "all"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"

class StockStatus(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"

# Phase 1 Configurable Default Thresholds
DEFAULT_MIN_PAIR_COUNT = 20
DEFAULT_MIN_CONFIDENCE = 0.30
DEFAULT_MIN_LIFT = 1.10
DEFAULT_MIN_PROFIT_MARGIN = 0.0
DEFAULT_BUNDLE_DISCOUNT_PCT = 0.10  # 10% bundle discount for customer incentive
