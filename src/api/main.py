from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import duckdb
import os
import jwt
from datetime import datetime, timedelta
import secrets

app = FastAPI(title="ETL Analytics API", version="1.0")

# Config
DB_PATH = os.getenv("DB_PATH", "data/etl.db")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db():
    """Get DuckDB connection"""
    return duckdb.connect(DB_PATH)

# Pydantic Models
class EmployeeBase(BaseModel):
    client_employee_id: str
    first_name: str
    last_name: str
    department_name: str
    date_joined: str

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department_name: Optional[str] = None

class TimesheetQuery(BaseModel):
    client_employee_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# AUTH - WORKING LOGIN
@app.post("/auth/login")
def login(request: LoginRequest):
    """Login leapfrog/leapfrog"""
    if request.username == "leapfrog" and request.password == "leapfrog":
        payload = {
            "sub": request.username,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256") 
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, 
        detail="❌ Invalid credentials. Use: leapfrog/leapfrog",
        headers={"WWW-Authenticate": "Bearer"}
        )

# HEALTH - PUBLIC
@app.get("/health")
def health():
    """Health check (public)"""
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return {"status": "healthy", "database": DB_PATH}
    except Exception as e:
        raise HTTPException(500, f"DB error: {str(e)}")

# EMPLOYEE CRUD - PROTECTED
@app.post("/employees/", status_code=201)
def create_employee(employee: EmployeeCreate, token=Depends(verify_token)):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO silver_employees 
            (client_employee_id, first_name, last_name, department_name, date_joined)
            VALUES (?, ?, ?, ?, ?)
        """, (employee.client_employee_id, employee.first_name, employee.last_name, employee.department_name, employee.date_joined))
        conn.commit()
        return {"message": "Employee created"}
    except Exception as e:
        raise HTTPException(400, f"Error: {str(e)}")
    finally:
        conn.close()

@app.get("/employees/")
def get_employees(limit: int = 100, token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute(f"SELECT * FROM silver_employees LIMIT {limit}").fetchall()
    columns = [desc[0] for desc in conn.description]
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return data

@app.get("/employees/{emp_id}")
def get_employee(emp_id: str, token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("SELECT * FROM silver_employees WHERE client_employee_id = ?", (emp_id,)).fetchone()
    columns = [desc[0] for desc in conn.description]
    conn.close()
    if result:
        return dict(zip(columns, result))
    raise HTTPException(404, "Employee not found")

@app.put("/employees/{emp_id}")
def update_employee(emp_id: str, employee: EmployeeUpdate, token=Depends(verify_token)):
    conn = get_db()
    updates = []
    params = []
    if employee.first_name is not None:
        updates.append("first_name = ?"); params.append(employee.first_name)
    if employee.last_name is not None:
        updates.append("last_name = ?"); params.append(employee.last_name)
    if employee.department_name is not None:
        updates.append("department_name = ?"); params.append(employee.department_name)
    
    if not updates:
        raise HTTPException(400, "No fields to update")
    
    params.append(emp_id)
    query = f"UPDATE silver_employees SET {', '.join(updates)} WHERE client_employee_id = ?"
    result = conn.execute(query, params).rowcount
    conn.commit()
    conn.close()
    
    if result == 0:
        raise HTTPException(404, "Not found")
    return {"message": "Updated"}

@app.delete("/employees/{emp_id}")
def delete_employee(emp_id: str, token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("DELETE FROM silver_employees WHERE client_employee_id = ?", (emp_id,)).rowcount
    conn.commit()
    conn.close()
    if result == 0:
        raise HTTPException(404, "Not found")
    return {"message": "Deleted"}

# TIMESHEETS - PROTECTED
@app.get("/timesheets/")
def get_timesheets(client_employee_id: Optional[str] = None, start_date: Optional[str] = None, 
                  end_date: Optional[str] = None, limit: int = 100, token=Depends(verify_token)):
    conn = get_db()
    query = "SELECT * FROM silver_timesheets"
    params = []
    conditions = []
    
    if client_employee_id:
        conditions.append("client_employee_id = ?"); params.append(client_employee_id)
    if start_date:
        conditions.append("punch_apply_date >= ?"); params.append(start_date)
    if end_date:
        conditions.append("punch_apply_date <= ?"); params.append(end_date)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += f" ORDER BY punch_apply_date DESC LIMIT {limit}"
    
    result = conn.execute(query, params).fetchall()
    columns = [desc[0] for desc in conn.description]
    data = [dict(zip(columns, row)) for row in result]
    conn.close()
    return {"data": data, "count": len(data)}

# KPIS - PROTECTED
# [Keep all your imports and models exactly the same until KPIs]

# KPIS - ALL 9 PROTECTED ENDPOINTS (Fixed)
@app.get("/kpis/active-headcount")
def get_active_headcount(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT month, active_headcount 
        FROM kpi_active_headcount 
        ORDER BY month DESC LIMIT 12
    """).fetchall()
    data = [{"month": r[0], "active_headcount": r[1]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/turnover")
def get_turnover(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT month, terminations, turnover_rate 
        FROM kpi_turnover_trend 
        ORDER BY month DESC LIMIT 12
    """).fetchall()
    data = [{"month": r[0], "terminations": r[1], "turnover_rate": r[2]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/tenure")
def get_tenure(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT department_name, ROUND(avg_tenure_years, 2) as avg_tenure_years, employee_count
        FROM kpi_avg_tenure 
        ORDER BY avg_tenure_years DESC
    """).fetchall()
    data = [{"department": r[0], "avg_years": r[1], "count": r[2]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/late-arrivals")
def get_late_arrivals(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT client_employee_id, late_count, ROUND(avg_minutes_late, 1) as avg_minutes_late
        FROM kpi_late_arrivals 
        ORDER BY late_count DESC LIMIT 20
    """).fetchall()
    data = [{"employee_id": r[0], "late_count": r[1], "avg_min_late": r[2]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/overtime")
def get_overtime(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT client_employee_id, overtime_days, ROUND(total_extra_hours, 1) as total_extra_hours
        FROM kpi_overtime 
        ORDER BY overtime_days DESC LIMIT 20
    """).fetchall()
    data = [{"employee_id": r[0], "overtime_days": r[1], "extra_hours": r[2]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/attrition")
def get_attrition(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT attrition_type, count 
        FROM kpi_early_attrition 
        ORDER BY count DESC
    """).fetchall()
    data = [{"type": r[0], "count": r[1]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/avg-working-hours")
def get_avg_working_hours(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT client_employee_id, week, ROUND(avghours, 1), daysworked
        FROM kpi_avg_working_hours 
        ORDER BY week DESC LIMIT 20
    """).fetchall()
    data = [{"employee": r[0], "week": r[1], "avg_hours": r[2], "days": r[3]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/early-departures")
def get_early_departures(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT client_employee_id, early_count, ROUND(avg_minutes_early, 1)
        FROM kpi_early_departures 
        ORDER BY early_count DESC LIMIT 20
    """).fetchall()
    data = [{"employee_id": r[0], "early_count": r[1], "avg_min_early": r[2]} for r in result]
    conn.close()
    return {"data": data}

@app.get("/kpis/rolling-avg-hours")
def get_rolling_avg_hours(token=Depends(verify_token)):
    conn = get_db()
    result = conn.execute("""
        SELECT client_employee_id, punch_apply_date, ROUND(rolling30dayavg, 1)
        FROM kpi_rolling_avg 
        ORDER BY punch_apply_date DESC LIMIT 50
    """).fetchall()
    data = [{"employee": r[0], "date": r[1], "rolling_30d_avg": r[2]} for r in result]
    conn.close()
    return {"data": data}


# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
