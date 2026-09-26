import os

# Configurable Training Thresholds for Data Sufficiency
MIN_TRANSACTIONS_FOR_ML = int(os.getenv("MIN_TRANSACTIONS_FOR_ML", "5000"))
MIN_HISTORICAL_DAYS = int(os.getenv("MIN_HISTORICAL_DAYS", "90"))
MIN_VALID_BASKETS = int(os.getenv("MIN_VALID_BASKETS", "3000"))
MIN_PRODUCT_TRANSACTIONS = int(os.getenv("MIN_PRODUCT_TRANSACTIONS", "50"))
MIN_PAIR_TRANSACTIONS = int(os.getenv("MIN_PAIR_TRANSACTIONS", "20"))
MIN_DATA_COMPLETENESS = float(os.getenv("MIN_DATA_COMPLETENESS", "0.90"))
MIN_MULTI_ITEM_BASKETS = int(os.getenv("MIN_MULTI_ITEM_BASKETS", "1000"))

# Retraining Triggers
RETRAIN_TRANSACTION_THRESHOLD = int(os.getenv("RETRAIN_TRANSACTION_THRESHOLD", "10000"))
RETRAIN_MIN_DAYS = int(os.getenv("RETRAIN_MIN_DAYS", "7"))

# Model Acceptance & Promotion
MAX_ALLOWED_MAE_DEGRADATION = float(os.getenv("MAX_ALLOWED_MAE_DEGRADATION", "0.05"))

# Model File Storage
MODEL_STORE_PATH = os.getenv("MODEL_STORE_PATH", "./backend/model_store")

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./restaurant_intelligence.db")

# ==========================================
# PHASE 3: REAL-TIME RECOMMENDATION SETTINGS
# ==========================================
MAX_RECOMMENDATIONS = int(os.getenv("MAX_RECOMMENDATIONS", "5"))

MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.30"))
MIN_LIFT = float(os.getenv("MIN_LIFT", "1.10"))
MIN_COMBO_PROFIT = float(os.getenv("MIN_COMBO_PROFIT", "0.0"))

# Configurable Recommendation Scoring Weights (Section 14 & 58)
ML_SCORE_WEIGHT = float(os.getenv("ML_SCORE_WEIGHT", "0.40"))
ASSOCIATION_WEIGHT = float(os.getenv("ASSOCIATION_WEIGHT", "0.25"))
RECENCY_WEIGHT = float(os.getenv("RECENCY_WEIGHT", "0.15"))
PROFIT_WEIGHT = float(os.getenv("PROFIT_WEIGHT", "0.15"))
AVAILABILITY_WEIGHT = float(os.getenv("AVAILABILITY_WEIGHT", "0.05"))

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
RECOMMENDATION_LATENCY_TARGET_MS = int(os.getenv("RECOMMENDATION_LATENCY_TARGET_MS", "500"))

