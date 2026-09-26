from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import Base, engine, SessionLocal
from backend.routes import transactions_router
from backend.routes import products_router
from backend.routes import analytics_router
from backend.routes import associations_router
from backend.routes import combos_router
from backend.routes import data_quality_router
from backend.routes import model_router
from backend.routes import recommendations_router
from backend.routes import customer_recommendations_router
from backend.routes import manager_recommendations_router
from backend.routes import carts_router
from backend.routes import recommendation_events_router
from backend.routes import pos_router
from backend.routes import inventory_router
from backend.routes import monitoring_router
from backend.services import evaluate_restaurant_data_sufficiency
from backend.services import get_active_model_record
from backend.services import train_combo_model_pipeline
from backend.services import log_event
from backend.models import Restaurant
from fastapi import HTTPException

# Create database tables (model_registry, training_jobs, transactions, carts, recommendation_events, etc.)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Restaurant Combo Intelligence API (Phase 3)",
    description=(
        "Production-grade Restaurant Combo Intelligence & Real-Time Recommendation Engine. "
        "Provides real-time cart-aware recommendations, POS integration with idempotency, "
        "live stock deduction, candidate ranking with 5-gate filters, manager analytics, "
        "and recommendation feedback tracking."
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 1 & 2 Routers
app.include_router(analytics_router)
app.include_router(products_router)
app.include_router(combos_router)
app.include_router(associations_router)
app.include_router(data_quality_router)
app.include_router(transactions_router)
app.include_router(model_router)

# Phase 3 Real-Time Routers
app.include_router(recommendations_router)
app.include_router(customer_recommendations_router)
app.include_router(manager_recommendations_router)
app.include_router(carts_router)
app.include_router(recommendation_events_router)
app.include_router(pos_router)
app.include_router(inventory_router)
app.include_router(monitoring_router)


@app.on_event("startup")
def on_startup_check_initial_training():
    """
    Section 30 & 59: Automatic Initial Training Onboarding.
    Checks if restaurant has sufficient data and lacks an active model;
    automatically trains and promotes model v1 without manual developer intervention.
    """
    db = SessionLocal()
    try:
        restaurant_id = "R001"
        active_model = get_active_model_record(db, restaurant_id)
        if not active_model:
            sufficiency = evaluate_restaurant_data_sufficiency(db, restaurant_id)
            if sufficiency["sufficient_for_ml"]:
                log_event("automatic initial training", restaurant_id, "Sufficient data detected on startup; initiating auto-training for model v1")
                train_combo_model_pipeline(db, restaurant_id, trigger="INITIAL_TRAINING")
            else:
                log_event("data sufficiency check", restaurant_id, f"Operating in rule-based mode: {sufficiency['reason']}")
    except Exception as e:
        log_event("startup error", "R001", f"Startup sufficiency verification error: {str(e)}")
    finally:
        db.close()

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "phase": 2,
        "engine": "Hybrid ML (XGBoost Regressor) + FP-Growth Rules Engine",
        "retraining": "Automatic (Threshold + Schedule)",
        "fallback": "Rule-Based Association & Profit Engine",
    }


@app.get("/api/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    db = SessionLocal()
    try:
        restaurant = db.query(Restaurant).filter(
            Restaurant.restaurant_id == restaurant_id,
            Restaurant.is_active == True,
        ).first()
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        return {
            "restaurant_id": restaurant.restaurant_id,
            "restaurant_name": restaurant.restaurant_name,
            "currency": restaurant.currency,
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
