import logging
from pathlib import Path
import pandas as pd
import duckdb
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.etl.config import config

class ETLPipeline:
    def __init__(self):
        self.conn = duckdb.connect(config.DB_PATH)
        logger.info(f"Connected to DuckDB: {config.DB_PATH}")
    
    def extract_employees(self):
        """Extract employee CSV"""
        logger.info("📥 Extracting employees...")
        emp_file = list(config.DATA_RAW_PATH.glob("employee*.csv"))[0]
        df = pd.read_csv(emp_file, sep='|', quotechar='"')
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        logger.info(f"✓ Extracted {len(df)} employee records")
        return df
    
    def extract_timesheets(self):
        """Extract & concatenate timesheet CSVs"""
        logger.info("📥 Extracting timesheets...")
        ts_files = sorted(config.DATA_RAW_PATH.glob("timesheet*.csv"))
        logger.info(f"Found {len(ts_files)} timesheet files: {[f.name for f in ts_files]}")
        
        dfs = []
        for ts_file in ts_files:
            logger.info(f"Reading {ts_file.name}...")
            df = pd.read_csv(ts_file, sep='|', quotechar='"', low_memory=False)
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
            dfs.append(df)
            logger.info(f"  ✓ {ts_file.name}: {len(df)} records")
        
        result = pd.concat(dfs, ignore_index=True)
        logger.info(f"✓ Extracted {len(result)} timesheet records from {len(ts_files)} files")
        return result
    
    def load_bronze(self, emp_df, ts_df):
        """Load raw data to BRONZE layer (DuckDB)"""
        logger.info("📤 Loading to BRONZE layer...")
        self.conn.execute("DROP TABLE IF EXISTS bronze_employees")
        self.conn.execute("DROP TABLE IF EXISTS bronze_timesheets")
        
        self.conn.register("temp_emp", emp_df)
        self.conn.execute("CREATE TABLE bronze_employees AS SELECT * FROM temp_emp")
        self.conn.unregister("temp_emp")
        logger.info(f"✓ Loaded {len(emp_df)} to bronze_employees")
        
        self.conn.register("temp_ts", ts_df)
        self.conn.execute("CREATE TABLE bronze_timesheets AS SELECT * FROM temp_ts")
        self.conn.unregister("temp_ts")
        logger.info(f"✓ Loaded {len(ts_df)} to bronze_timesheets")
    
    def transform_employees(self, emp_df):
        """Clean & validate employee data"""
        logger.info("🔄 Transforming employees...")
        
        # Make a copy to avoid SettingWithCopyWarning
        emp_df = emp_df.copy()
        
        # Remove duplicates
        emp_df = emp_df.drop_duplicates(subset=['client_employee_id'], keep='first')
        
        # Fix date columns
        for col in ['hire_date', 'term_date', 'dob']:
            if col in emp_df.columns:
                emp_df[col] = pd.to_datetime(emp_df[col], errors='coerce')
        
        # Add derived columns
        emp_df['is_active'] = emp_df['term_date'].isna().astype(int)
        emp_df['tenure_days'] = (emp_df['term_date'].fillna(pd.Timestamp.now().normalize()) - emp_df['hire_date']).dt.days
        
        logger.info(f"✓ Transformed {len(emp_df)} employees")
        return emp_df
    
    def transform_timesheets(self, ts_df):
        """Clean & validate timesheet data"""
        logger.info("🔄 Transforming timesheets...")
        
        # Make a copy to avoid SettingWithCopyWarning
        ts_df = ts_df.copy()
        
        # Remove duplicates
        ts_df = ts_df.drop_duplicates(subset=['client_employee_id', 'punch_in_datetime'], keep='first')
        
        # Fix datetime columns
        ts_df['punch_apply_date'] = pd.to_datetime(ts_df['punch_apply_date'], errors='coerce')
        ts_df['punch_in_datetime'] = pd.to_datetime(ts_df['punch_in_datetime'], errors='coerce')
        ts_df['punch_out_datetime'] = pd.to_datetime(ts_df['punch_out_datetime'], errors='coerce')
        ts_df['scheduled_start_datetime'] = pd.to_datetime(ts_df['scheduled_start_datetime'], errors='coerce')
        ts_df['scheduled_end_datetime'] = pd.to_datetime(ts_df['scheduled_end_datetime'], errors='coerce')
        
        # Calculate late/early arrivals (in minutes)
        ts_df['minutes_late'] = ((ts_df['punch_in_datetime'] - ts_df['scheduled_start_datetime']).dt.total_seconds() / 60).fillna(0)
        ts_df['minutes_early'] = ((ts_df['scheduled_end_datetime'] - ts_df['punch_out_datetime']).dt.total_seconds() / 60).fillna(0)
        
        # Mark anomalies (grace: ±5 min)
        ts_df['is_late'] = (ts_df['minutes_late'] > 5).astype(int)
        ts_df['is_early'] = (ts_df['minutes_early'] > 5).astype(int)
        ts_df['is_overtime'] = (ts_df['hours_worked'] > 8.5).astype(int)
        ts_df['is_normal_work'] = ((ts_df['hours_worked'] >= 7.5) & (ts_df['hours_worked'] <= 8.5)).astype(int)
        
        logger.info(f"✓ Transformed {len(ts_df)} timesheet records")
        return ts_df
    
    def load_silver(self, emp_df, ts_df):
        """Load cleaned data to SILVER layer (DuckDB)"""
        logger.info("📤 Loading to SILVER layer...")
        
        self.conn.register("temp_emp_silver", emp_df)
        self.conn.execute("CREATE TABLE silver_employees AS SELECT * FROM temp_emp_silver")
        self.conn.unregister("temp_emp_silver")
        logger.info(f"✓ Loaded {len(emp_df)} to silver_employees")
        
        self.conn.register("temp_ts_silver", ts_df)
        self.conn.execute("CREATE TABLE silver_timesheets AS SELECT * FROM temp_ts_silver")
        self.conn.unregister("temp_ts_silver")
        logger.info(f"✓ Loaded {len(ts_df)} to silver_timesheets")
    
    def generate_kpis(self):
        """Generate all 9 KPI tables in GOLD layer"""
        logger.info("🏆 Generating KPIs...")
        
        kpis = [
            ("kpi_active_headcount", """
                SELECT 
                    DATE_TRUNC('month', punch_apply_date)::date AS month,
                    COUNT(DISTINCT CASE 
                        WHEN e.hire_date <= ts.punch_apply_date 
                        AND (e.term_date IS NULL OR e.term_date > ts.punch_apply_date)
                        THEN e.client_employee_id 
                    END) AS active_headcount
                FROM silver_timesheets ts
                CROSS JOIN (SELECT DISTINCT client_employee_id, hire_date, term_date FROM silver_employees) e
                GROUP BY DATE_TRUNC('month', punch_apply_date)
                ORDER BY month DESC
            """),
            ("kpi_turnover_trend", """
                SELECT 
                    DATE_TRUNC('month', term_date)::date AS month,
                    COUNT(*) AS terminations
                FROM silver_employees
                WHERE term_date IS NOT NULL
                GROUP BY DATE_TRUNC('month', term_date)
                ORDER BY month DESC
            """),
            ("kpi_avg_tenure", """
                SELECT 
                    department_name,
                    ROUND(AVG(tenure_days) / 365.25, 2) AS avg_tenure_years,
                    COUNT(*) AS employee_count
                FROM silver_employees
                WHERE department_name IS NOT NULL
                GROUP BY department_name
                ORDER BY avg_tenure_years DESC
            """),
            ("kpi_avg_working_hours", """
                SELECT 
                    client_employee_id,
                    DATE_TRUNC('week', punch_apply_date)::date AS week,
                    ROUND(AVG(hours_worked), 2) AS avg_hours,
                    COUNT(*) AS days_worked
                FROM silver_timesheets
                WHERE is_normal_work = 1
                GROUP BY client_employee_id, DATE_TRUNC('week', punch_apply_date)
                ORDER BY week DESC
                LIMIT 1000
            """),
            ("kpi_late_arrivals", """
                SELECT 
                    client_employee_id,
                    COUNT(*) AS late_count,
                    ROUND(AVG(minutes_late), 2) AS avg_minutes_late
                FROM silver_timesheets
                WHERE is_late = 1
                GROUP BY client_employee_id
                ORDER BY late_count DESC
                LIMIT 100
            """),
            ("kpi_early_departures", """
                SELECT 
                    client_employee_id,
                    COUNT(*) AS early_count,
                    ROUND(AVG(minutes_early), 2) AS avg_minutes_early
                FROM silver_timesheets
                WHERE is_early = 1
                GROUP BY client_employee_id
                ORDER BY early_count DESC
                LIMIT 100
            """),
            ("kpi_overtime", """
                SELECT 
                    client_employee_id,
                    COUNT(*) AS overtime_days,
                    ROUND(SUM(hours_worked - 8), 2) AS total_extra_hours
                FROM silver_timesheets
                WHERE is_overtime = 1
                GROUP BY client_employee_id
                ORDER BY overtime_days DESC
                LIMIT 100
            """),
            ("kpi_rolling_avg", """
                SELECT 
                    client_employee_id,
                    punch_apply_date,
                    ROUND(AVG(hours_worked) OVER (
                        PARTITION BY client_employee_id 
                        ORDER BY punch_apply_date 
                        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                    ), 2) AS rolling_30day_avg
                FROM silver_timesheets
                ORDER BY punch_apply_date DESC
                LIMIT 5000
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
                AND (term_date - hire_date) >= interval '90 days'
            """),
        ]
        
        for table_name, query in kpis:
            try:
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                self.conn.execute(f"CREATE TABLE {table_name} AS {query}")
                count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchall()[0][0]
                logger.info(f"✓ {table_name}: {count} rows")
            except Exception as e:
                logger.warning(f"⚠️ {table_name}: {str(e)}")
    
    def validate_data_quality(self):
        """Run quality checks"""
        logger.info("✅ Running data quality checks...")
        
        emp_count = self.conn.execute("SELECT COUNT(*) FROM silver_employees").fetchall()[0][0]
        ts_count = self.conn.execute("SELECT COUNT(*) FROM silver_timesheets").fetchall()[0][0]
        
        logger.info(f"Data Quality: {emp_count} employees, {ts_count} timesheets")
    
    def run(self):
        """Execute full ETL pipeline"""
        logger.info("🚀 Starting ETL Pipeline...")
        
        try:
            # Extract
            emp_df = self.extract_employees()
            ts_df = self.extract_timesheets()
            
            # Load Bronze
            self.load_bronze(emp_df, ts_df)
            
            # Transform
            emp_clean = self.transform_employees(emp_df)
            ts_clean = self.transform_timesheets(ts_df)
            
            # Load Silver
            self.load_silver(emp_clean, ts_clean)
            
            # Quality & KPIs
            self.validate_data_quality()
            self.generate_kpis()
            
            logger.info("✅ ETL Pipeline completed successfully!")
            logger.info(f"📊 Database: {config.DB_PATH}")
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}", exc_info=True)
            raise
        finally:
            self.conn.close()


if __name__ == "__main__":
    pipeline = ETLPipeline()
    pipeline.run()