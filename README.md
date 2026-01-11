# ETL to Insights: Employee Data Pipeline

**Author:** Dikshant Bikram Thapa  
**Date:** January, 2026  
**Architecture:** Medallion Architecture

## Installation & Setup

### Step 1: Clone Repository
```bash
git clone <repo-url>
cd ETL-Project
```

### Step 2: Create Virtual Environment
```bash
#Make sure that 3.11 version is installed (MANDATORY)
python3.11 -m venv venv
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

### Step 5: Prepare Data Directory (OPTIONAL : if have data loaded)
```bash
mkdir -p data/raw data/bronze data/silver data/gold
# Copy CSV files to data/raw/
cp /path/to/employee_*.csv data/raw/
cp /path/to/timesheet_*.csv data/raw/
```
---

## Running the Pipeline

### Step 1: Run ETL Pipeline
```bash
python -m src.etl.flows
```

### Starting the API Server

```bash
python -m uvicorn src.api.main:app --reload
```

```bash
curl http://localhost:8000/docs
curl http://localhost:8000/health
curl http://localhost:8000/kpis/active-headcount
curl http://localhost:8000/kpis/turnover
curl http://localhost:8000/kpis/tenure
curl http://localhost:8000/kpis/late-arrivals
curl http://localhost:8000/kpis/overtime
and more...
```
## Visualizations

### Generating Charts

```bash
python -m src.viz.charts
```
### Viewing Charts

```bash

open reports/01_active_headcount.html
open reports/02_turnover_trend.html

```
---