# src/viz/charts.py
import plotly.express as px

# 1. Active Headcount Trend
fig1 = px.line(df_headcount, x='month', y='active_headcount', 
               title='Active Headcount Over Time',
               markers=True)

# 2. Turnover by Department (Bar Chart)
fig2 = px.bar(df_turnover, x='department', y='terminations',
              color='month',
              title='Monthly Turnover by Department')

# 3. Overtime vs Productivity Scatter
fig3 = px.scatter(df_productivity, x='overtime_hours', y='avg_working_hours',
                  size='employee_id', hover_data=['department'],
                  title='Overtime Impact on Working Hours')

# Save as HTML (interactive)
fig1.write_html('visualizations/headcount_trend.html')
