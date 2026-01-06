# ETL to Insights: Employee Data Pipeline

**Author:** Dikshant Bikram Thapa  
**Date:** January 6, 2026  
**Architecture:** Medallion Architecture

## 💻 Installation & Setup

### Step 1: Clone Repository
```bash
git clone <repo-url>
cd data-onboarding-etl
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create Environment Configuration
```bash
cat > .env << 'EOF'
DB_PATH=data/etl.db
LOG_LEVEL=INFO
BATCH_SIZE=1000
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET=your-secret-key-change-in-production
EOF
```

### Step 5: Prepare Data Directory
```bash
mkdir -p data/raw data/bronze data/silver data/gold
# Copy CSV files to data/raw/
cp /path/to/employee_*.csv data/raw/
cp /path/to/timesheet_*.csv data/raw/
```
---

## 🚀 Running the Pipeline
### Step 1: Activate Virtual Environment
```bash
source venv/bin/activate
```

### Step 2: Run ETL Pipeline
```bash
python -m src.etl.flows
```

### Starting the API Server

```bash
source venv/bin/activate
python -m uvicorn src.api.main:app --reload
```

```bash
curl http://localhost:8000/health
curl http://localhost:8000/kpis/active-headcount
curl http://localhost:8000/kpis/turnover
curl http://localhost:8000/kpis/tenure
curl http://localhost:8000/kpis/late-arrivals
curl http://localhost:8000/kpis/overtime
```
## 📊 Visualizations

### Generating Charts

```bash
python src/viz/charts.py
```
### Viewing Charts

```bash

open reports/01_active_headcount.html
open reports/02_turnover_trend.html

```
---

## 🛠️ Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11 |
| Data Processing | Pandas | 2.x |
| Database | DuckDB | Latest |
| API Framework | FastAPI | Latest |
| Visualization | Plotly | Latest |
| Environment | Virtual Environment (venv) | |
| Version Control | Git | |

---
