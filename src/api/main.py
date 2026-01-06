# src/api/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredential
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
import logging

from src.etl.config import config

# ==================== SETUP ====================

logger = logging.getLogger(__name__)
Base = declarative_base()
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
security = HTTPBearer()

app = FastAPI(
    title="ETL to Insights API",
    description="HR Analytics API with Employee Management & Timesheet Tracking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== SCHEMAS ====================

class EmployeeCreate(BaseModel):
    client_employee_id: str
    first_name: str
    last_name: str
    department_name: str
    job_title: str
    hire_date: datetime
    scheduled_weekly_hour: int

class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    department_name: str | None = None
    job_title: str | None = None

class EmployeeResponse(BaseModel):
    client_employee_id: str
    first_name: str
    last_name: str
    department_name: str
    job_title: str
    hire_date: datetime
    is_active: int

    class Config:
        from_attributes = True

class TimesheetResponse(BaseModel):
    client_employee_id: str
    punch_apply_date: datetime
    hours_worked: float
    is_late: int
    is_early: int
    is_overtime: int

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ==================== AUTH ====================

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthCredential = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== ROUTES ====================

@app.post("/auth/token", response_model=TokenResponse)
async def login():
    """Generate JWT token for API access"""
    access_token = create_access_token(
        data={"sub": "etl-user"},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token}

# ========== EMPLOYEE CRUD ==========

@app.post("/employees", response_model=EmployeeResponse, tags=["Employees"])
async def create_employee(
    emp: EmployeeCreate,
    credentials: HTTPAuthCredential = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new employee"""
    await verify_token(credentials)
    
    try:
        # Insert into PostgreSQL
        query = f"""
            INSERT INTO silver_employees 
            (client_employee_id, first_name, last_name, department_name, job_title, hire_date, scheduled_weekly_hour)
            VALUES ('{emp.client_employee_id}', '{emp.first_name}', '{emp.last_name}', 
                   '{emp.department_name}', '{emp.job_title}', '{emp.hire_date}', {emp.scheduled_weekly_hour})
            RETURNING *
        """
        result = db.execute(query)
        db.commit()
        logger.info(f"✓ Created employee {emp.client_employee_id}")
        return emp
    except Exception as e:
        logger.error(f"✗ Create employee failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/employees/{emp_id}", response_model=EmployeeResponse, tags=["Employees"])
async def get_employee(emp_id: str, db: Session = Depends(get_db)):
    """Retrieve employee by ID"""
    try:
        from sqlalchemy import text
        result = db.execute(
            text(f"SELECT * FROM silver_employees WHERE client_employee_id = :id"),
            {"id": emp_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return result
    except Exception as e:
        logger.error(f"✗ Get employee failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/employees", response_model=list[EmployeeResponse], tags=["Employees"])
async def list_employees(department: str | None = None, db: Session = Depends(get_db)):
    """List all employees (with optional department filter)"""
    try:
        from sqlalchemy import text
        
        query = "SELECT * FROM silver_employees"
        if department:
            query += f" WHERE department_name = '{department}'"
        
        results = db.execute(text(query)).fetchall()
        return results
    except Exception as e:
        logger.error(f"✗ List employees failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/employees/{emp_id}", response_model=dict, tags=["Employees"])
async def update_employee(
    emp_id: str,
    emp_update: EmployeeUpdate,
    credentials: HTTPAuthCredential = Depends(security),
    db: Session = Depends(get_db)
):
    """Update employee details"""
    await verify_token(credentials)
    
    try:
        from sqlalchemy import text
        
        update_fields = []
        if emp_update.first_name:
            update_fields.append(f"first_name = '{emp_update.first_name}'")
        if emp_update.last_name:
            update_fields.append(f"last_name = '{emp_update.last_name}'")
        if emp_update.department_name:
            update_fields.append(f"department_name = '{emp_update.department_name}'")
        if emp_update.job_title:
            update_fields.append(f"job_title = '{emp_update.job_title}'")
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_sql = f"UPDATE silver_employees SET {', '.join(update_fields)} WHERE client_employee_id = '{emp_id}'"
        db.execute(text(update_sql))
        db.commit()
        
        logger.info(f"✓ Updated employee {emp_id}")
        return {"status": "updated", "employee_id": emp_id}
    except Exception as e:
        logger.error(f"✗ Update employee failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/employees/{emp_id}", response_model=dict, tags=["Employees"])
async def delete_employee(
    emp_id: str,
    credentials: HTTPAuthCredential = Depends(security),
    db: Session = Depends(get_db)
):
    """Soft delete employee (mark as inactive)"""
    await verify_token(credentials)
    
    try:
        from sqlalchemy import text
        
        db.execute(text(f"UPDATE silver_employees SET active_status = 0 WHERE client_employee_id = '{emp_id}'"))
        db.commit()
        
        logger.info(f"✓ Deleted (soft) employee {emp_id}")
        return {"status": "deleted", "employee_id": emp_id}
    except Exception as e:
        logger.error(f"✗ Delete employee failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ========== TIMESHEET (READ-ONLY) ==========

@app.get("/timesheets", response_model=list[TimesheetResponse], tags=["Timesheets"])
async def get_timesheets(
    emp_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db)
):
    """Retrieve timesheets with optional filters"""
    try:
        from sqlalchemy import text
        
        query = "SELECT client_employee_id, punch_apply_date, hours_worked, is_late, is_early, is_overtime FROM silver_timesheets WHERE 1=1"
        
        if emp_id:
            query += f" AND client_employee_id = '{emp_id}'"
        if start_date:
            query += f" AND punch_apply_date >= '{start_date}'"
        if end_date:
            query += f" AND punch_apply_date <= '{end_date}'"
        
        query += " ORDER BY punch_apply_date DESC LIMIT 1000"
        
        results = db.execute(text(query)).fetchall()
        return results
    except Exception as e:
        logger.error(f"✗ Get timesheets failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ========== HEALTH CHECK ==========

@app.get("/health", tags=["Health"])
async def health_check():
    """API health status"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, log_level="info")
