# src/etl/flows.py
import logging
from datetime import datetime
from prefect import flow, task
from prefect.logging import get_run_logger
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
import glob

from .config import config

logger = logging.getLogger(__name__)

# ==================== EXTRACT TASKS ====================

@task(retries=2, retry_delay_seconds=10, name="Extract Employee CSV")
def extract_employees():
    """Extract employee.csv with proper delimiter"""
    log = get_run_logger()
    try:
        emp_file = list(Path(config.DATA_RAW_PATH).glob("employee*.csv"))[0]
        log.info(f"Reading {emp_file}")
        
        df = pd.read_csv(
            emp_file,
            delimiter='|',
            quotechar='"',
            dtype={'client_employee_id': str, 'manager_employee_id': str}
        )
        
        # Initial cleaning
        df.columns = df.columns.str.strip()
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        
        log.info(f"✓ Extracted {len(df)} employee records")
        return df
    except Exception as e:
        log.error(f"✗ Employee extraction failed: {str(e)}")
        raise

@task(retries=2, retry_delay_seconds=10, name="Extract Timesheet CSVs")
def extract_timesheets():
    """Extract all timesheet*.csv files and concatenate"""
    log = get_run_logger()
    try:
        ts_files = sorted(Path(config.DATA_RAW_PATH).glob("timesheet*.csv"))
        log.info(f"Found {len(ts_files)} timesheet files: {[f.name for f in ts_files]}")
        
        dfs = []
        for ts_file in ts_files:
            log.info(f"Reading {ts_file.name}...")
            df = pd.read_csv(
                ts_file,
                delimiter='|',
                quotechar='"',
                dtype={'client_employee_id': str}
            )
            df.columns = df.columns.str.strip()
            dfs.append(df)
        
        result = pd.concat(dfs, ignore_index=True)
        log.info(f"✓ Extracted {len(result)} timesheet records from {len(ts_files)} files")
        return result
    except Exception as e:
        log.error(f"✗ Timesheet extraction failed: {str(e)}")
        raise

# ==================== LOAD TASKS ====================

@task(retries=2, retry_delay_seconds=10, name="Load to BRONZE")
def load_to_bronze(emp_df, ts_df):
    """Load raw data to PostgreSQL bronze layer"""
    log = get_run_logger()
    try:
        engine = create_engine(config.DATABASE_URL)
        
        # Drop existing bronze tables (for fresh runs)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS bronze_timesheets CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS bronze_employees CASCADE"))
            conn.commit()
        
        # Load employees
        emp_df.to_sql('bronze_employees', engine, if_exists='replace', index=False)
        log.info(f"✓ Loaded {len(emp_df)} employees to BRONZE")
        
        # Load timesheets
        ts_df.to_sql('bronze_timesheets', engine, if_exists='replace', index=False, chunksize=5000)
        log.info(f"✓ Loaded {len(ts_df)} timesheets to BRONZE")
        
        engine.dispose()
    except Exception as e:
        log.error(f"✗ BRONZE load failed: {str(e)}")
        raise

# ==================== TRANSFORM TASKS ====================

@task(name="Transform Employees → SILVER")
def transform_employees(emp_df):
    """Clean and validate employee data"""
    log = get_run_logger()
    try:
        # Remove duplicates
        emp_df = emp_df.drop_duplicates(subset=['client_employee_id'], keep='first')
        log.info(f"✓ Removed duplicates → {len(emp_df)} records")
        
        # Fix date columns
        for col in ['hire_date', 'term_date', 'dob', 'job_start_date']:
            if col in emp_df.columns:
                emp_df[col] = pd.to_datetime(emp_df[col], errors='coerce')
        
        # Clean nulls
        emp_df['active_status'] = emp_df['active_status'].fillna(1)
        emp_df['fte_status'] = emp_df['fte_status'].fillna('Unknown')
        
        # Derived columns
        emp_df['is_active'] = (emp_df['term_date'].isna()).astype(int)
        emp_df['tenure_days'] = (
            (emp_df['term_date'].fillna(datetime.now()) - emp_df['hire_date']).dt.days
        )
        
        log.info(f"✓ Transformed {len(emp_df)} employee records")
        return emp_df
    except Exception as e:
        log.error(f"✗ Employee transformation failed: {str(e)}")
        raise

@task(name="Transform Timesheets → SILVER")
def transform_timesheets(ts_df):
    """Clean and validate timesheet data"""
    log = get_run_logger()
    try:
        # Remove duplicates
        ts_df = ts_df.drop_duplicates(subset=['client_employee_id', 'punch_in_datetime'], keep='first')
        log.info(f"✓ Removed duplicates → {len(ts_df)} records")
        
        # Fix date columns
        ts_df['punch_apply_date'] = pd.to_datetime(ts_df['punch_apply_date'], errors='coerce')
        ts_df['punch_in_datetime'] = pd.to_datetime(ts_df['punch_in_datetime'], errors='coerce')
        ts_df['punch_out_datetime'] = pd.to_datetime(ts_df['punch_out_datetime'], errors='coerce')
        ts_df['scheduled_start_datetime'] = pd.to_datetime(ts_df['scheduled_start_datetime'], errors='coerce')
        ts_df['scheduled_end_datetime'] = pd.to_datetime(ts_df['scheduled_end_datetime'], errors='coerce')
        
        # Filter for productivity metrics (normal work only)
        ts_df['is_normal_work'] = ts_df['pay_code'].str.contains('normal_worked', case=False, na=False).astype(int)
        
        # Calculate late/early
        ts_df['minutes_late'] = (
            (ts_df['punch_in_datetime'] - ts_df['scheduled_start_datetime']).dt.total_seconds() / 60
        ).fillna(0)
        ts_df['minutes_early'] = (
            (ts_df['scheduled_end_datetime'] - ts_df['punch_out_datetime']).dt.total_seconds() / 60
        ).fillna(0)
        
        # Mark anomalies (grace period: ±5 min)
        ts_df['is_late'] = (ts_df['minutes_late'] > 5).astype(int)
        ts_df['is_early'] = (ts_df['minutes_early'] > 5).astype(int)
        ts_df['is_overtime'] = (ts_df['hours_worked'] > 8.5).astype(int)
        
        log.info(f"✓ Transformed {len(ts_df)} timesheet records")
        return ts_df
    except Exception as e:
        log.error(f"✗ Timesheet transformation failed: {str(e)}")
        raise

@task(name="Load to SILVER")
def load_to_silver(emp_df, ts_df):
    """Persist transformed data to SILVER layer"""
    log = get_run_logger()
    try:
        engine = create_engine(config.DATABASE_URL)
        
        emp_df.to_sql('silver_employees', engine, if_exists='replace', index=False)
        log.info(f"✓ Loaded {len(emp_df)} employees to SILVER")
        
        ts_df.to_sql('silver_timesheets', engine, if_exists='replace', index=False, chunksize=5000)
        log.info(f"✓ Loaded {len(ts_df)} timesheets to SILVER")
        
        engine.dispose()
    except Exception as e:
        log.error(f"✗ SILVER load failed: {str(e)}")
        raise

# ==================== KPI GENERATION ====================

@task(name="Generate KPI Tables (GOLD)")
def generate_kpis():
    """Execute all 9 KPI queries and populate GOLD layer"""
    log = get_run_logger()
    try:
        engine = create_engine(config.DATABASE_URL)
        
        kpi_queries = [
            ("kpi_active_headcount", """
                SELECT 
                    DATE_TRUNC('month', punch_apply_date)::date AS month,
                    COUNT(DISTINCT CASE 
                        WHEN e.hire_date <= punch_apply_date 
                        AND (e.term_date IS NULL OR e.term_date > punch_apply_date)
                        THEN e.client_employee_id 
                    END) AS active_headcount
                FROM silver_timesheets ts
                CROSS JOIN (SELECT DISTINCT client_employee_id, hire_date, term_date FROM silver_employees) e
                GROUP BY DATE_TRUNC('month', punch_apply_date)
                ORDER BY month DESC;
            """),
            ("kpi_turnover_trend", """
                SELECT 
                    DATE_TRUNC('month', term_date)::date AS month,
                    COUNT(*) AS terminations
                FROM silver_employees
                WHERE term_date IS NOT NULL
                GROUP BY DATE_TRUNC('month', term_date)
                ORDER BY month DESC;
            """),
            ("kpi_avg_tenure", """
                SELECT 
                    department_name,
                    ROUND(AVG(tenure_days) / 365.25, 2) AS avg_tenure_years,
                    COUNT(*) AS employee_count
                FROM silver_employees
                WHERE department_name IS NOT NULL
                GROUP BY department_name
                ORDER BY avg_tenure_years DESC;
            """),
            ("kpi_avg_working_hours", """
                SELECT 
                    client_employee_id,
                    DATE_TRUNC('week', punch_apply_date)::date AS week,
                    ROUND(AVG(hours_worked)::numeric, 2) AS avg_hours,
                    COUNT(*) AS days_worked
                FROM silver_timesheets
                WHERE is_normal_work = 1
                GROUP BY client_employee_id, DATE_TRUNC('week', punch_apply_date)
                ORDER BY week DESC, avg_hours DESC;
            """),
            ("kpi_late_arrivals", """
                SELECT 
                    client_employee_id,
                    COUNT(*) AS late_arrival_count,
                    ROUND(AVG(minutes_late)::numeric, 2) AS avg_minutes_late
                FROM silver_timesheets
                WHERE is_late = 1 AND is_normal_work = 1
                GROUP BY client_employee_id
                ORDER BY late_arrival_count DESC;
            """),
            ("kpi_early_departures", """
                SELECT 
                    client_employee_id,
                    COUNT(*) AS early_departure_count,
                    ROUND(AVG(minutes_early)::numeric, 2) AS avg_minutes_early
                FROM silver_timesheets
                WHERE is_early = 1 AND is_normal_work = 1
                GROUP BY client_employee_id
                ORDER BY early_departure_count DESC;
            """),
            ("kpi_overtime", """
                SELECT 
                    client_employee_id,
                    COUNT(*) AS overtime_days,
                    ROUND(SUM(hours_worked - 8)::numeric, 2) AS total_extra_hours
                FROM silver_timesheets
                WHERE is_overtime = 1 AND is_normal_work = 1
                GROUP BY client_employee_id
                ORDER BY overtime_days DESC;
            """),
            ("kpi_rolling_avg", """
                SELECT 
                    client_employee_id,
                    punch_apply_date,
                    ROUND(AVG(hours_worked) OVER (
                        PARTITION BY client_employee_id 
                        ORDER BY punch_apply_date 
                        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                    )::numeric, 2) AS rolling_30day_avg
                FROM silver_timesheets
                WHERE is_normal_work = 1
                ORDER BY punch_apply_date DESC;
            """),
            ("kpi_early_attrition", """
                SELECT 
                    'Early Attrition (<90 days)' AS attrition_type,
                    COUNT(*) AS count
                FROM silver_employees
                WHERE term_date IS NOT NULL 
                AND (term_date - hire_date) < interval '90 days'
                UNION ALL
                SELECT 
                    'Other Attrition (≥90 days)' AS attrition_type,
                    COUNT(*) AS count
                FROM silver_employees
                WHERE term_date IS NOT NULL 
                AND (term_date - hire_date) >= interval '90 days';
            """),
        ]
        
        for table_name, query in kpi_queries:
            log.info(f"Generating {table_name}...")
            with engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                conn.execute(text(f"CREATE TABLE {table_name} AS {query}"))
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                conn.commit()
                log.info(f"✓ {table_name}: {count} rows")
        
        engine.dispose()
    except Exception as e:
        log.error(f"✗ KPI generation failed: {str(e)}")
        raise

# ==================== DATA QUALITY CHECKS ====================

@task(name="Data Quality Validation")
def validate_data_quality():
    """Run quality checks on loaded data"""
    log = get_run_logger()
    try:
        engine = create_engine(config.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check row counts
            emp_count = conn.execute(text("SELECT COUNT(*) FROM silver_employees")).scalar()
            ts_count = conn.execute(text("SELECT COUNT(*) FROM silver_timesheets")).scalar()
            
            log.info(f"Quality Check: {emp_count} employees, {ts_count} timesheets")
            
            # Check nulls in critical columns
            null_check = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN client_employee_id IS NULL THEN 1 END) as null_ids,
                    COUNT(CASE WHEN hire_date IS NULL THEN 1 END) as null_dates
                FROM silver_employees
            """)).fetchone()
            
            log.info(f"Null check - Total: {null_check[0]}, Null IDs: {null_check[1]}, Null Dates: {null_check[2]}")
            
            if null_check[1] > 0:
                log.warning(f"⚠️ Found {null_check[1]} NULL employee IDs!")
            
            log.info("✓ Data quality validation passed")
        
        engine.dispose()
    except Exception as e:
        log.error(f"✗ Quality check failed: {str(e)}")
        raise

# ==================== MAIN ORCHESTRATION FLOW ====================

@flow(name="etl-to-insights-pipeline", log_prints=True)
def etl_pipeline():
    """Main ETL orchestration with proper task dependencies"""
    log = get_run_logger()
    log.info("🚀 Starting ETL Pipeline...")
    
    # 1. EXTRACT
    log.info("Phase 1: EXTRACT")
    emp_df = extract_employees()
    ts_df = extract_timesheets()
    
    # 2. LOAD BRONZE
    log.info("Phase 2: LOAD BRONZE")
    load_to_bronze(emp_df, ts_df)
    
    # 3. TRANSFORM
    log.info("Phase 3: TRANSFORM → SILVER")
    emp_clean = transform_employees(emp_df)
    ts_clean = transform_timesheets(ts_df)
    
    # 4. LOAD SILVER
    log.info("Phase 4: LOAD SILVER")
    load_to_silver(emp_clean, ts_clean)
    
    # 5. QUALITY & KPIS
    log.info("Phase 5: QUALITY CHECKS & KPI GENERATION")
    validate_data_quality()
    generate_kpis()
    
    log.info("✅ ETL Pipeline completed successfully!")

if __name__ == "__main__":
    etl_pipeline()
