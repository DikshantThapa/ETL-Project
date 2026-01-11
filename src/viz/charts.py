import duckdb
import plotly.express as px
import plotly.graph_objects as go
import os
import pandas as pd
from src.etl.config import config

def generate_charts():
    """Generate interactive Plotly charts for all 9 KPIs"""
    conn = duckdb.connect(config.DB_PATH)
    os.makedirs('reports', exist_ok=True)
    
    # Chart 1: Active Headcount Over Time
    df1 = conn.execute("SELECT * FROM kpi_active_headcount ORDER BY month").df()
    df1['month'] = pd.to_datetime(df1['month']).dt.strftime('%Y-%m')
    fig1 = px.line(df1, x='month', y='active_headcount',
                   title='Active Headcount Over Time',
                   markers=True, template='plotly_dark')
    fig1.write_html('reports/01_active_headcount.html')
    print("✓ Generated: 01_active_headcount.html")
    
    # Chart 2: Turnover by Month
    df2 = conn.execute("SELECT * FROM kpi_turnover_trend ORDER BY month").df()
    df2['month'] = pd.to_datetime(df2['month']).dt.strftime('%Y-%m')
    fig2 = px.bar(df2, x='month', y='terminations',
                  title='Monthly Turnover Trend',
                  template='plotly_dark')
    fig2.write_html('reports/02_turnover_trend.html')
    print("✓ Generated: 02_turnover_trend.html")
    
    # Chart 3: Tenure by Department
    df3 = conn.execute("SELECT * FROM kpi_avg_tenure ORDER BY avg_tenure_years DESC").df()
    fig3 = px.bar(df3, x='department_name', y='avg_tenure_years',
                  color='employee_count',
                  title='Average Tenure by Department',
                  template='plotly_dark')
    fig3.write_html('reports/03_tenure_by_dept.html')
    print("✓ Generated: 03_tenure_by_dept.html")
    
    # Chart 4: Late Arrivals Distribution
    df4 = conn.execute("SELECT * FROM kpi_late_arrivals ORDER BY late_count DESC LIMIT 20").df()
    fig4 = px.bar(df4, x='client_employee_id', y='late_count',
                  title='Top 20 Employees with Late Arrivals',
                  template='plotly_dark')
    fig4.write_html('reports/04_late_arrivals.html')
    print("✓ Generated: 04_late_arrivals.html")
    
    # Chart 5: Overtime Distribution
    df5 = conn.execute("SELECT * FROM kpi_overtime ORDER BY overtime_days DESC LIMIT 20").df()
    fig5 = px.bar(df5, x='client_employee_id', y='total_extra_hours',
                  title='Top 20 Employees with Overtime Hours',
                  template='plotly_dark')
    fig5.write_html('reports/05_overtime.html')
    print("✓ Generated: 05_overtime.html")
    
    # Chart 6: Attrition Type Distribution (Got FULL PIE BECAUSE 6 and 0 is the data that i got)
    df6 = conn.execute("SELECT * FROM kpi_early_attrition").df()
    if len(df6) > 0:
        fig6 = px.pie(df6, names='attrition_type', values='count',
                      title='Attrition Type Distribution',
                      template='plotly_dark')
        fig6.write_html('reports/06_attrition_type.html')
        print("✓ Generated: 06_attrition_type.html")
    
    # Chart 7: Average Working Hours by Week - FIXED: Aggregate by week
    df7 = conn.execute("""
        SELECT week, ROUND(AVG(avg_hours), 2) as avg_hours_all, COUNT(DISTINCT client_employee_id) as num_employees
        FROM kpi_avg_working_hours
        GROUP BY week
        ORDER BY week DESC
        LIMIT 50
    """).df()
    if len(df7) > 0:
        df7['week'] = pd.to_datetime(df7['week']).dt.strftime('%Y-%m-%d')
        fig7 = px.line(df7, x='week', y='avg_hours_all',
                       title='Average Working Hours by Week (All Employees)',
                       markers=True, template='plotly_dark',
                       hover_data=['num_employees'],
                       labels={'avg_hours_all': 'Avg Hours', 'num_employees': 'Employees'})
        fig7.write_html('reports/07_avg_working_hours.html')
        print("✓ Generated: 07_avg_working_hours.html")
    
    # Chart 8: Early Departures Distribution
    df8 = conn.execute("SELECT * FROM kpi_early_departures ORDER BY early_count DESC LIMIT 20").df()
    if len(df8) > 0:
        fig8 = px.bar(df8, x='client_employee_id', y='early_count',
                      title='Top 20 Employees with Early Departures (>5min)',
                      template='plotly_dark')
        fig8.write_html('reports/08_early_departures.html')
        print("✓ Generated: 08_early_departures.html")
    
    # Chart 9: Rolling 30-Day Average Hours - FIXED: (Sample 10 random employees)
    df9_all = conn.execute("SELECT DISTINCT client_employee_id FROM kpi_rolling_avg ORDER BY RANDOM() LIMIT 10").df()
    
    if len(df9_all) > 0:
        employees = df9_all['client_employee_id'].tolist()
        placeholders = ','.join(['?' for _ in employees])
        df9 = conn.execute(f"""
            SELECT client_employee_id, punch_apply_date, rolling_30day_avg
            FROM kpi_rolling_avg
            WHERE client_employee_id IN ({placeholders})
            ORDER BY punch_apply_date DESC
        """, employees).df()
        
        if len(df9) > 0:
            df9['punch_apply_date'] = pd.to_datetime(df9['punch_apply_date']).dt.strftime('%Y-%m-%d')
            fig9 = px.line(df9, x='punch_apply_date', y='rolling_30day_avg',
                           color='client_employee_id',
                           title='Rolling 30-Day Average Hours (10 Sample Employees)',
                           template='plotly_dark',
                           labels={'punch_apply_date': 'Date', 'rolling_30day_avg': 'Rolling Avg (30d)'})
            fig9.write_html('reports/09_rolling_avg_hours.html')
            print("✓ Generated: 09_rolling_avg_hours.html")
    
    conn.close()
    print("\n✅ All 9 visualizations generated in reports/ folder!")

if __name__ == "__main__":
    generate_charts()