# Restaurant Combo Intelligence

The customer-facing dashboard is focused on restaurant sales: top-selling products, historical basket associations, combo recommendations, and transparent per-combo profit calculations. The React app reads from the FastAPI backend and its configured SQLAlchemy database; the Node server continues to serve the frontend and retain existing POS/API functionality.

## Run the application

Install the declared Python dependencies once, then start the API and dashboard in separate terminals from the project root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
npm run dev
```

Open `http://localhost:3000`. Set `VITE_API_BASE_URL` at build time if the FastAPI service is hosted somewhere other than `http://localhost:8000`. The default database is `restaurant_intelligence.db`; `DATABASE_URL` can point the backend at the restaurant's configured database.

The dashboard defaults to the last 30 days and supports today, 7 days, 30 days, 90 days, and custom ranges. Combo candidates are mined from transactions containing the selected range's top ten products. Pair occurrence is counted once per transaction, regardless of line-item quantity. Support, directional confidence, and lift are calculated from completed, paid restaurant orders.

The existing trained model ranks candidates when an active restaurant model is available. If inference cannot run, the dashboard uses the configured rule fallback (at least 20 paired transactions, 30% confidence, lift above 1.10, and non-negative combo profit). It does not manufacture model predictions. Profit values are calculated as:

```text
normal price = product A price + product B price
combo cost = product A cost + product B cost
customer saving = normal price - combo price
normal profit = (price A - cost A) + (price B - cost B)
combo profit = combo price - combo cost
profit difference = combo profit - normal profit
```

Model administration, POS, validation, and monitoring APIs remain in the backend; they are not part of the main dashboard UI.

---

## 🎯 Architecture Overview

Restaurant Combo Intelligence is designed around a strict separation of concerns between historical descriptive statistics and future performance prediction:

1. **Phase 1 — Historical Association (Descriptive)**:
   * "Which items were purchased together in the past?"
   * Computed via **FP-Growth** frequent itemset mining on verified database transactions.
   * Calculates actual **Support**, **Confidence**, **Lift**, and co-purchase frequencies.
   * Computes unit economics (regular sum, combo cost, discounted price, gross profit, and margin).

2. **Phase 2 — Future Combo Performance Prediction (Predictive)**:
   * "Based on historical co-occurrence, recent sales velocity, product economics, and price elasticity, how many units of a candidate combo will sell in a future period?"
   * Trained using **Gradient Boosting Regressors** / **Random Forests** evaluated against a **Linear Baseline**.
   * Time-based chronological split (**Train / Validation / Test**) preventing future data leakage.
   * Fully governed by a **Model Registry** tracking MAE, RMSE, MAPE, $R^2$, and Precision@10.
   * Features **Automatic Initial Training**, **Automatic Retraining** (upon 10,000 new transactions), **Safe Rollback**, and seamless **Rule-Based Fallback** when data is insufficient.

---

## 🏗️ Full Project Directory Structure

```text
Market_basket_analysis/
??? backend/
?   ??? main.py
?   ??? config.py
?   ??? database.py
?   ??? models.py
?   ??? schemas.py
?   ??? services.py
?   ??? ml.py
?   ??? routes.py
?   ??? utils.py
??? src/
?   ??? App.tsx
?   ??? components.tsx
?   ??? index.css
?   ??? main.tsx
?   ??? types.ts
??? data/
?   ??? demo_transactions.csv
??? tests/                         # Retained because npm test uses this suite
??? scripts.py                     # Optional demo-data, seed, POS, and ML commands
??? server.ts                      # Node server, data store, and combo analysis
??? package.json
??? package-lock.json
??? requirements.txt
??? tsconfig.json
??? vite.config.ts
??? index.html
??? .env.example
??? .gitignore
??? README.md
```

---

## 🚦 Data Sufficiency Engine & Rules

The system never attempts machine learning on thin or noisy data. Before training or ML inference:

| Gate | Requirement | Rule |
|------|-------------|------|
| **1. Transaction Volume** | $\ge 5,000$ valid transactions | Avoids overfitting on small sample sizes |
| **2. Historical Span** | $\ge 90$ days of transaction history | Captures weekday vs. weekend & meal-period variance |
| **3. Valid Baskets** | $\ge 500$ multi-item baskets | Ensures basket co-occurrence signals exist |
| **4. Product Tx Coverage** | $\ge 30$ transactions per product | Ensures statistical stability of product metrics |
| **5. Pair Frequency** | $\ge 15$ co-purchases per combo pair | Ensures statistically meaningful co-occurrence |
| **6. Data Quality** | $\ge 90\%$ data completeness | No missing timestamps, negative prices, or orphan IDs |

### Decision Logic:
* **All Gates Passed** $\rightarrow$ `ML_ACTIVE` mode (Gradient Boosting regression predicts future demand).
* **Any Gate Failed** $\rightarrow$ `RULE_BASED` mode (FP-Growth co-occurrence + Profit Engine).
* Managers can audit all 6 gates in real-time via the **Data Sufficiency Inspector** in the UI.

---

## 🔬 Feature Engineering Pipeline

For every candidate pair $(A, B)$, the system extracts 15+ normalized features over rolling windows:

1. **Market Basket Signals**:
   * Historical Co-occurrence Count
   * Historical Support, Confidence $(A \rightarrow B)$, Confidence $(B \rightarrow A)$, and Lift
2. **Sales Velocity**:
   * Recent 30-day and 7-day transaction frequency of Item A and Item B
   * Trend ratio: $\frac{\text{Sales}_{7d} \times 4.28}{\text{Sales}_{30d}}$ (identifies rising vs. declining combos)
3. **Unit Economics & Margin**:
   * Combined regular price, food cost, and standalone margin %
   * Recommended combo price and customer savings discount %
4. **Channel Affinity**:
   * Dine-in vs. Delivery vs. Takeaway historical mix

---

## ⏱️ Chronological Validation & Model Registry

* **Time-Based Splitting**:
  * **Train Set**: First 70% of chronological timeline
  * **Validation Set**: Next 15% of timeline (hyperparameter tuning & candidate evaluation)
  * **Test Set**: Final 15% of timeline (out-of-sample benchmarking)
  * *Zero random shuffling* to prevent temporal look-ahead data leakage.
* **Champion / Challenger Promotion Policy**:
  * A new candidate model is promoted to `ACTIVE` **only if**:
    $$\text{RMSE}_{\text{candidate}} < \text{RMSE}_{\text{active}} \quad \text{AND} \quad \text{Precision@10}_{\text{candidate}} \ge \text{Precision@10}_{\text{active}}$$
  * If the candidate model degrades performance, it is marked `REJECTED`, and the existing champion model remains live without downtime.
* **One-Click Rollback**:
  * Any previous active model version (e.g. `v1.0.0`) can be restored instantly via `POST /api/model/rollback/:version` or through the **Model History Modal** in the UI.

---

## 🔄 Automatic Retraining Triggers

The system automatically tracks transaction increments without human intervention:

1. **Transaction Counter**: Every new POS order increments `new_transactions_since_training`.
2. **Retraining Threshold**: When `new_transactions_since_training >= 10,000`, the system automatically:
   * Re-evaluates Data Sufficiency.
   * Re-extracts rolling-window features.
   * Fits a challenger model version (e.g. `v2.0.0`).
   * Evaluates validation metrics against the active champion model.
   * Promotes or rejects with zero downtime.
3. **Startup Auto-Training**: On initial startup, if the database has sufficient data and no active model exists, the engine automatically trains and activates model `v1.0.0`.

---

## 🌐 API Reference

### Active Simple Sales & Combo Analysis
The dashboard reads actual completed, paid transaction data from the FastAPI database. The default period is the last 30 days; top-selling products and combos accept `filter=today|7days|30days|90days|custom` and optional `start_date`/`end_date` values. Combo discovery uses the selected period's ten top-selling products and defaults to at least 20 pair transactions, 0.30 directional confidence, lift greater than 1.10, and non-negative combo profit. An active historical model ranks eligible candidates; otherwise deterministic association and profit rules are used.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/restaurants/:restaurantId` | `GET` | Restaurant name and currency |
| `/api/products/top-selling` | `GET` | Selected-range quantity, order count, revenue, and profit |
| `/api/combos` | `GET` | FP-Growth pair candidates with model or rule ranking and combo economics |

Combo responses include pair count, support, both directional confidence values, lift, normal price/profit, combo price/cost/profit, customer saving, and profit difference. Inventory, validation, model administration, and monitoring routes remain backend-only.

### Phase 1: Analytics, Products & Combos
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard` | `GET` | Aggregated revenue, gross profit, top items & channel split |
| `/api/products/top-selling` | `GET` | Top products sorted by quantity, revenue, or profit |
| `/api/associations` | `GET` | FP-Growth association rules (Support, Confidence, Lift) |
| `/api/combos` | `GET` | Recommended combos with pricing, cost, margin, and sales |
| `/api/combos/:id/price` | `POST` | Update custom selling price for a combo |
| `/api/data-quality` | `GET` | Automated POS validation report |
| `/api/transactions` | `POST` | Record a new POS transaction |
| `/api/transactions/import-csv` | `POST` | Batch import transactions from CSV |
| `/api/transactions/sample-csv` | `GET` | Download sample CSV template |

### Phase 2: ML Model Registry & Retraining
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/model/status` | `GET` | Active model version, type, training stats, and retrain countdown |
| `/api/model/metrics` | `GET` | Detailed MAE, RMSE, MAPE, $R^2$, and Precision@10 metrics |
| `/api/model/data-sufficiency` | `GET` | Real-time 6-gate data sufficiency audit |
| `/api/model/history` | `GET` | Model Registry version list with promotion timestamps and metrics |
| `/api/model/train` | `POST` | Trigger model training pipeline |
| `/api/model/retrain` | `POST` | Trigger automated retraining check |
| `/api/model/rollback/:version` | `POST` | Roll back active model to a previous version |
| `/api/sufficiency` | `GET` | Sufficiency status & threshold definitions |
| `/api/sufficiency/thresholds` | `PUT` | Update managerial sufficiency thresholds or simulation overrides |

---

## 🚀 Getting Started

### 1. Run the Full-Stack Web Application (UI + Server)
```bash
npm run dev
```
The application runs on `http://localhost:3000`.

### 2. Run the Simple Combo Analysis Tests
```bash
npm test
```

### 3. Standalone Python CLI ML Training (Legacy / Optional)
```bash
python scripts.py train-model --restaurant R001
```

### 4. Stream Simulated POS Orders to Test Retraining Triggers (Legacy / Optional)
```bash
python scripts.py simulate-pos-stream --count 50 --delay 0.05
```

### 5. Generate and Seed Demo Data
```bash
python scripts.py generate-demo-data
python scripts.py seed-database
```
Seeding resets the configured demo SQLite database before importing `data/demo_transactions.csv`.

### 6. Reset Demo State
Click the **"Reset Demo"** button in the UI header or call:
```bash
curl -X POST http://localhost:3000/api/database/reset
```
