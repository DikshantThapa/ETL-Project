import duckdb
import plotly.express as px
import os
from src.etl.config import config

def generate_charts():
    """Generate interactive Plotly charts"""
    conn = duckdb.connect(config.DB_PATH)
    
    # Ensure reports directory exists
    os.makedirs('reports', exist_ok=True)
    
    # Chart 1: Active Headcount Over Time
    df_headcount = conn.execute("SELECT * FROM kpi_active_headcount ORDER BY month").fetchall()
    df1 = conn.execute("SELECT * FROM kpi_active_headcount ORDER BY month").df()
    fig1 = px.line(df1, x='month', y='active_headcount', 
                   title='Active Headcount Over Time',
                   markers=True, template='plotly_dark')
    fig1.write_html('reports/01_active_headcount.html')
    print("✓ Generated: 01_active_headcount.html")
    
    # Chart 2: Turnover by Month
    df2 = conn.execute("SELECT * FROM kpi_turnover_trend ORDER BY month").df()
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
    
    # Chart 6: Early Attrition vs Long-term
    df6 = conn.execute("SELECT * FROM kpi_early_attrition").df()
    fig6 = px.pie(df6, names='attrition_type', values='count',
                  title='Attrition Type Distribution',
                  template='plotly_dark')
    fig6.write_html('reports/06_attrition_type.html')
    print("✓ Generated: 06_attrition_type.html")
    
    conn.close()
    print("\n✅ All visualizations generated in reports/ folder!")

if __name__ == "__main__":
    generate_charts()