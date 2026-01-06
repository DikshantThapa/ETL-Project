from fastapi import FastAPI
import duckdb
import os

app = FastAPI(title="ETL Analytics API", version="1.0")

# Database path
DB_PATH = "data/etl.db"

def get_db():
    """Get DuckDB connection"""
    return duckdb.connect(DB_PATH)

@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy", "database": DB_PATH}

@app.get("/kpis/active-headcount")
def get_active_headcount():
    """Get active headcount over time"""
    conn = get_db()
    result = conn.execute("SELECT * FROM kpi_active_headcount ORDER BY month DESC").fetchall()
    columns = ['month', 'active_headcount']
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/turnover")
def get_turnover():
    """Get turnover trend"""
    conn = get_db()
    result = conn.execute("SELECT * FROM kpi_turnover_trend ORDER BY month DESC").fetchall()
    columns = ['month', 'terminations']
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/tenure")
def get_tenure():
    """Get average tenure by department"""
    conn = get_db()
    result = conn.execute("SELECT * FROM kpi_avg_tenure ORDER BY avg_tenure_years DESC").fetchall()
    columns = ['department_name', 'avg_tenure_years', 'employee_count']
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/late-arrivals")
def get_late_arrivals():
    """Get late arrivals"""
    conn = get_db()
    result = conn.execute("SELECT * FROM kpi_late_arrivals ORDER BY late_count DESC LIMIT 20").fetchall()
    columns = ['client_employee_id', 'late_count', 'avg_minutes_late']
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/overtime")
def get_overtime():
    """Get overtime data"""
    conn = get_db()
    result = conn.execute("SELECT * FROM kpi_overtime ORDER BY overtime_days DESC LIMIT 20").fetchall()
    columns = ['client_employee_id', 'overtime_days', 'total_extra_hours']
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/attrition")
def get_attrition():
    """Get attrition analysis"""
    conn = get_db()
    result = conn.execute("SELECT * FROM kpi_early_attrition").fetchall()
    columns = ['attrition_type', 'count']
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return {"data": data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)