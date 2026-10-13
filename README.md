# DEMANDIQ AI

**AI-Powered Demand Forecasting & Inventory Optimization**

> *"Predict Demand. Optimize Inventory. Decide Smarter."*

---

## 1. Executive Overview

**DemandIQ AI** is an enterprise-grade predictive analytics and inventory optimization platform. It bridges advanced time-series machine learning with classical supply-chain operations research to answer fundamental business questions:

- **What will customer demand be?** (Multi-horizon probabilistic forecasts: 7, 14, 30, 60, 90 days)
- **Which products require replenishment right now?** (Dynamic Reorder Point thresholds)
- **When should inventory be reordered?** (Lead-time demand modeling)
- **How much should be ordered?** (Recommended Order Quantity formula clamped to zero)
- **Which products are at critical stockout risk?** (Early-warning depletion detection)
- **Which products are overstocked?** (Surplus capital & inventory coverage analysis)
- **Which forecasting model performs best?** (Leakage-free cross-validation across Baselines, Linear, Random Forest, and XGBoost)

DemandIQ AI shares the same **luminous glassmorphism, typography precision, and component quality** established in the ORVION design system, delivering a SaaS experience built for operations directors, data scientists, inventory planners, and executives.

---

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15 (containerized via `docker-compose.yml`)
- Node.js (for dashboard build)

### Environment
Copy `.env.example` to `.env` and set `DATABASE_URL=` pointing to the Docker Postgres service (`demandiq-user:...@postgres:5432/demandiq`). Do not commit `.env`.

### Database & Migrations
```bash
# Apply migrations (use container env; do not hardcode credentials)
alembic upgrade head
```
The current production revision is `2b7a91f8e3d1`. The previous base is `c48bc7184d59`.

### Admin creation
```bash
python scripts/create_first_admin.py
```

### Run services
```bash
docker-compose up -d postgres api
# Dashboard optionally
# docker-compose up -d dashboard
```

### Health / Status
- `/api/v1/system/status`
- `/api/v1/auth/me` (authenticated)
- `/api/v1/models`

### Authentication
Role-based access (`VIEWER`, `EDITOR`, `ADMIN`). Token-based session auth via `Session` table; password hashed with bcrypt. Admin creation is script-based; no hardcoded admin fallback remains.

### Testing
```bash
pytest tests/unit/test_auth.py
```

### Backup
A custom backup `demandiq_backup_2026-10-13.dump` exists; do not stage it.

---

## 2. Core Architecture & Workflow

```
RAW DATA (Historical Sales + Inventory)
   │
   ▼
INGESTION & SCHEMA VALIDATION (Null, duplicate, negative price checks)
   │
   ▼
CLEANING & TIME-SERIES EXPANSION (Distinguishes true zero demand from missing days)
   │
   ▼
FEATURE PIPELINE (Calendar, Lags 1/7/14/28, Rolling Windows with strict shift(1) zero-leakage)
   │
   ▼
CHRONOLOGICAL SPLIT (70% Train / 15% Validation / 15% Holdout Test)
   │
   ▼
MODEL ARENA EVALUATION
   ├── Naive Forecast
   ├── 7-Day Moving Average
   ├── Seasonal Naive (7-Day DOW)
   ├── Ridge Linear Regression
   ├── Random Forest Regressor
   └── XGBoost Regressor
   │
   ▼
CHAMPION MODEL SELECTION (Validation WAPE / MAE benchmark)
   │
   ▼
PRODUCTION FORECASTING SERVICE (Expanding confidence interval bounds)
   │
   ▼
INVENTORY OPTIMIZATION ENGINE
   ├── Lead-Time Demand = ADD × LeadTime
   ├── Safety Stock = Z × σ × √L  (Configurable 95% service level)
   ├── Reorder Point (ROP) = LTD + SS
   └── Recommended Order Quantity = Target - Stock - OnOrder
   │
   ▼
FASTAPI REST LAYER (/api/v1)
   │
   ▼
REACT 19 + THREE.JS DASHBOARD ("Demand Intelligence World")
```

---

## 3. Technology Stack

| Layer | Technologies |
|---|---|
| **Language & Runtime** | Python 3.11+ / Node.js 20+ |
| **Data Processing** | Pandas, NumPy, SciPy (Normal distribution $Z$-factor) |
| **Machine Learning** | Scikit-learn, XGBoost, Joblib |
| **REST API** | FastAPI, Uvicorn, Pydantic v2, Starlette |
| **Database ORM** | SQLAlchemy 2.0 (PostgreSQL production-ready; SQLite local development) |
| **Frontend Framework** | React 19, TypeScript, Vite |
| **Styling & Design System** | Tailwind CSS v4, Lucide Icons, Glassmorphism Tokens |
| **3D & Visualizations** | Three.js (Demand Intelligence World), Recharts (Area, Composed, Bar) |
| **Testing** | Pytest, FastAPI TestClient, Unit & Data-Leakage Tests |
| **Containerization** | Docker, Docker Compose (Multi-stage build) |

---

## 4. Dataset Specification & Data Dictionary

Raw transactions are accepted in CSV or direct SQL table format (`data/raw/historical_sales.csv`):

| Column | Type | Description |
|---|---|---|
| `date` | Date (YYYY-MM-DD) | Transaction or calendar sales date |
| `product_id` | String | Unique SKU identifier (e.g., `P001`) |
| `product_name` | String | Commercial product catalog name |
| `category` | String | Product taxonomy (Electronics, Industrial, etc.) |
| `quantity_sold` | Float / Int | Units sold on the given date (clamped $\ge 0$) |
| `unit_price` | Float | Unit selling price in USD |
| `revenue` | Float | Gross revenue (`quantity_sold * unit_price`) |
| `inventory_level` | Float | Current physical available inventory units |
| `lead_time_days` | Float | Supplier replenishment turnaround time in days |

### Data Validation Rules:
- **Missing Dates**: Flagged and interpolated through time-index complete reindexing.
- **Negative Quantities**: Sanitized to 0 unless flagged explicitly as returns.
- **Negative Prices**: Strictly rejected.
- **Duplicates**: Deduplicated on `(date, product_id)`.
- **Health Score**: Computes an automated 0–100 data quality rating.

---

## 5. Feature Engineering & Zero-Leakage Guarantee

All temporal features are constructed with mathematical prevention of target leakage:
- **Calendar Features**: `day`, `day_of_week`, `week_of_year`, `month`, `quarter`, `year`, `is_weekend`, `is_month_start`, `is_month_end`.
- **Lag Features**: `lag_1`, `lag_7`, `lag_14`, `lag_28` (previous periods).
- **Rolling Features**: `rolling_mean_7`, `rolling_mean_14`, `rolling_mean_28`, `rolling_std_7`, `rolling_std_14`, `rolling_std_28`.
- **CRITICAL**: `.shift(1)` is strictly applied prior to rolling window aggregations, ensuring that current and future observations never influence historical predictive rows.

---

## 6. Inventory Optimization Mathematical Formulas

### 1. Lead-Time Demand (LTD)
$$\text{Lead-Time Demand} = \text{Average Daily Demand} \times \text{Lead Time}$$
*Example: $20 \text{ units/day} \times 7 \text{ days} = 140 \text{ units}$*

### 2. Safety Stock (SS)
$$\text{Safety Stock} = Z \times \sigma \times \sqrt{L}$$
Where:
- $Z$ = Normal distribution factor ($Z = 1.645$ for 95% service level)
- $\sigma$ = Standard deviation of daily demand
- $L$ = Supplier lead time in days

### 3. Reorder Point (ROP)
$$\text{Reorder Point} = \text{Lead-Time Demand} + \text{Safety Stock}$$
*Example: $140 + 30 = 170 \text{ units}$*

### 4. Recommended Order Quantity (ROQ)
$$\text{Target Stock} = \text{Forecast Demand for Planning Horizon} + \text{Safety Stock}$$
$$\text{ROQ} = \max\left(0, \, \text{Target Stock} - \text{Current Inventory} - \text{On-Order Quantity}\right)$$

### 5. Risk Classification & Explainability
- **CRITICAL**: Projected inventory reaches 0 before replenishment arrives ($\text{Days Until Stockout} < \text{Lead Time}$).
- **HIGH**: Available inventory approaches or breaches safety buffer ($\text{Stock} \le \text{ROP}$ and approaching $\text{Safety Stock}$).
- **MEDIUM**: Stock is below reorder threshold ($\text{Stock} \le \text{ROP}$).
- **OVERSTOCK**: Current stock exceeds target stock by $>35\%$ or coverage exceeds $4 \times \text{Lead Time}$.
- **LOW / HEALTHY**: Stock is safely above reorder threshold.

---

## 7. Installation & Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- Git

### 1. Clone & Set Up Python Environment
```bash
git clone <repo-url>
cd demandiq-ai

# Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example environment configuration
copy .env.example .env
```

### 3. Generate Historical Data & Train Production Pipeline
```bash
# 1. Generate realistic multi-category dataset (365 days, 12 products)
python scripts/generate_dataset.py

# 2. Train baseline and ML models, evaluate holdout metrics, select champion model, and seed DB
python scripts/train_model.py
```

### 4. Start the FastAPI REST Backend
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at: `http://localhost:8000/docs`

### 5. Start the Frontend Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Dashboard will be available at: `http://localhost:5173`

---

## 8. Automated Testing Suite

Run all unit, integration, and leakage prevention tests with Pytest:
```bash
pytest -v
```

Tests verify:
1. `test_business_logic_example`: Confirms $ADD=20$, $L=7$, $SS=30 \implies LTD=140, ROP=170$. If stock = $80$, replenishment is triggered.
2. `test_order_quantity_clamping_to_zero`: Prevents surplus orders when stock is elevated.
3. `test_zero_demand_coverage_handling`: Eliminates zero-division hazards on inactive products.
4. `test_no_data_leakage_in_features`: Confirms day $T$ spikes cannot affect day $T$ rolling statistics.
5. `test_chronological_split_strict_ordering`: Verifies time-series train/val/test boundary integrity.
6. API endpoint integration tests (`/health`, `/products`, `/forecasts`, `/inventory/recommendations`, standard error responses).

---

## 9. REST API Endpoints Reference

Base URL: `/api/v1`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health probe |
| `GET` | `/system/status` | Measured diagnostics (DB, API, Model, Freshness) |
| `GET` | `/products` | List all catalog SKUs (supports `?category=`) |
| `GET` | `/products/{product_id}` | Detailed product metadata and current stock |
| `POST` | `/products` | Add new catalog product |
| `POST` | `/forecasts` | Generate $N$-day forecast (`product_id`, `horizon_days`) |
| `GET` | `/forecasts/history` | Historical forecast logs |
| `GET` | `/inventory/recommendations` | Active replenishment decisions (supports `?risk=`, `?category=`) |
| `GET` | `/inventory/optimization/{product_id}` | Mathematical parameters breakdown for SKU |
| `GET` | `/dashboard/summary` | Aggregated executive KPIs, category demand, and alerts |
| `GET` | `/models` | Model registry and algorithm comparison table |
| `POST` | `/models/train` | Triggers full retraining & champion model re-selection |
| `POST` | `/models/{version}/promote` | Promotes model version to production traffic |
| `GET` | `/data/quality` | Dataset validation and cleaning audit report |

---

## 10. Docker Deployment

Deploy the entire stack with Docker Compose:

```bash
docker-compose up -d --build
```

Services:
- **`postgres`**: Production PostgreSQL 15 database (`5432:5432`)
- **`api`**: FastAPI REST service with live model loading (`8000:8000`)
- **`dashboard`**: Nginx container serving compiled React dashboard (`5173:80`)

---

## 11. Role-Based Access Control (RBAC)

The system supports role-based operational permissions:
- **ADMIN**: Unrestricted system administration, product creation, model retraining, and promotion.
- **DATA_SCIENTIST**: Model evaluation, feature engineering audits, dataset re-training.
- **INVENTORY_MANAGER**: Stock adjustments, reorder decision approvals, lead-time configuration.
- **ANALYST**: Deep forecast analytics, actual vs predicted tracking, performance trends.
- **OPERATIONS_MANAGER**: Purchase order export, supply chain lead time audits.
- **VIEWER**: Read-only oversight.

---

## 12. Troubleshooting & FAQ

- **Where are model artifacts saved?**
  Production model: `models/production/demand_model.joblib` and `models/production/metadata.json`.
  Historical versions: `models/experiments/`.
- **How to switch to PostgreSQL?**
  Set `DATABASE_URL=postgresql://user:password@localhost:5432/demandiq` in `.env`.
- **Can I run the dashboard without 3D?**
  Yes. Click the **"Reduced Motion"** toggle in the bottom corner of the 3D viewport to engage the lightweight 2D performance mode.

---

## License & Attribution

Designed and engineered for **DemandIQ AI** under the MIT License.
Visual design language and component standard aligned with the ORVION product family.
