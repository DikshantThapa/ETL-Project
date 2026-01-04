from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

app = FastAPI()
security = HTTPBearer()

# Employee CRUD
@app.post("/employees")
async def create_employee(emp: EmployeeSchema, token = Depends(security)):
    # Verify token, insert
    return {"id": emp_id, "status": "created"}

@app.get("/employees/{emp_id}")
async def get_employee(emp_id: int):
    return db.query(Employee).filter_by(id=emp_id).first()

@app.put("/employees/{emp_id}")
async def update_employee(emp_id: int, data: EmployeeUpdate, token = Depends(security)):
    # Verify auth, update
    return {"status": "updated"}

@app.delete("/employees/{emp_id}")
async def delete_employee(emp_id: int, token = Depends(security)):
    # Soft delete
    return {"status": "deleted"}

# Timesheet Read-only
@app.get("/timesheets")
async def get_timesheets(emp_id: int = None, start_date: str = None, end_date: str = None):
    query = db.query(Timesheet)
    if emp_id:
        query = query.filter_by(employee_id=emp_id)
    if start_date:
        query = query.filter(Timesheet.date >= start_date)
    return query.all()
