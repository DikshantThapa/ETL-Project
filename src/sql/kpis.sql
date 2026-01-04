SELECT 
    DATE_TRUNC('month', t.date) AS month,
    COUNT(DISTINCT CASE 
        WHEN e.date_joined <= t.date 
        AND (e.termination_date IS NULL OR e.termination_date > t.date)
        THEN e.employee_id 
    END) AS active_headcount
FROM timesheet t
CROSS JOIN employees e
GROUP BY DATE_TRUNC('month', t.date);

SELECT 
    DATE_TRUNC('month', termination_date) AS month,
    COUNT(*) AS terminations
FROM employees
WHERE termination_date IS NOT NULL
GROUP BY DATE_TRUNC('month', termination_date);


SELECT 
    department,
    AVG(EXTRACT(DAY FROM (
        COALESCE(termination_date, NOW()) - date_joined
    ))::numeric / 365.25) AS avg_tenure_years
FROM employees
GROUP BY department;


SELECT 
    employee_id,
    DATE_TRUNC('week', date) AS week,
    AVG(hours_worked) AS avg_hours
FROM timesheet
GROUP BY employee_id, DATE_TRUNC('week', date);


SELECT 
    employee_id,
    COUNT(*) AS late_arrivals
FROM timesheet
WHERE EXTRACT(EPOCH FROM (actual_start_time - scheduled_start_time))/60 > 5
GROUP BY employee_id;


SELECT 
    employee_id,
    COUNT(*) AS early_departures
FROM timesheet
WHERE EXTRACT(EPOCH FROM (scheduled_end_time - actual_end_time))/60 > 5
GROUP BY employee_id;


SELECT 
    employee_id,
    COUNT(*) AS overtime_days
FROM timesheet
WHERE hours_worked > 8.5  
GROUP BY employee_id;


SELECT 
    employee_id,
    date,
    AVG(hours_worked) OVER (
        PARTITION BY employee_id 
        ORDER BY date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_30day_avg
FROM timesheet
ORDER BY employee_id, date;


SELECT 
    CASE 
        WHEN EXTRACT(MONTH FROM termination_date - date_joined) <= 3 
        THEN 'Early Attrition'
        ELSE 'Other'
    END AS attrition_type,
    COUNT(*) AS count
FROM employees
WHERE termination_date IS NOT NULL
GROUP BY attrition_type;