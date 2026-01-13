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
#python -m venv venv may cause problem in pendulum and prefect module conflicts in other than python 3.11
#if already 3.11 is installed
python -m venv venv can work
#⚠️ Python versions other than 3.11 may cause dependency conflicts (Prefect / Pendulum).
source venv/bin/activate        # Windows: venv\Scripts\activate
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

### Step 5: Prepare Data Directory (OPTIONAL : if you have already loaded the data somewhere)
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
or
python src/api/main.py
```
### Bearer TOKEN

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"leapfrog","password":"leapfrog"}' | jq -r .access_token)

echo "Token: $TOKEN"
# you get something like eyJhbGciOiJIUz.........
```

### Swagger UI

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/employees/
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/kpis/active-headcount
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/timesheets/?client_employee_id=401114"

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