# ETL to Insights Pipeline
## Architecture
- **Bronze**: Raw employee + timesheet CSVs loaded
- **Silver**: Cleaned, validated, deduplicated data
- **Gold**: KPI aggregates ready for analysis

## Setup
1. Clone repo
2. `cp .env.example .env` && fill DB_PASSWORD
3. `docker-compose up --build`
4. `python src/etl/flows.py` to run pipeline
5. Visit `http://localhost:8000/docs` for API

## Key Design Decisions
- **Prefect** over Luigi: Better logging, modern UI
- **PostgreSQL** for relational integrity + window functions
- **Plotly** for interactive viz (vs static Matplotlib)
- **Medallion architecture** for data quality gates

## Performance
- Indexed `employee_id`, `date` on timesheet (query speed)
- Incremental loads via timestamp (rerun safety)
