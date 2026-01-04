from prefect import flow, task
from prefect.logging import get_run_logger

@task(retries=2)
def extract_from_csv(file_path: str):
    """Extract with error handling"""
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    return df

@task
def transform_employees(df):
    """Clean: remove dupes, fix types, validate"""
    df = df.drop_duplicates(subset=['employee_id'])
    df['date_joined'] = pd.to_datetime(df['date_joined'])
    return df

@task
def load_to_db(df, table_name):
    """Load + validate"""
    with get_connection() as conn:
        df.to_sql(table_name, conn, if_exists='replace')
    
@flow(name="etl-pipeline")
def etl_pipeline():
    emp_raw = extract_from_csv('data/raw/employee.csv')
    ts_raw = extract_from_csv('data/raw/timesheet.csv')
    
    emp_clean = transform_employees(emp_raw)
    load_to_db(emp_clean, 'employees')