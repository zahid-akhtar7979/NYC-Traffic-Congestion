# NYC Traffic Congestion — Benchmarking Application

Benchmarking application for analyzing a congestion pricing analytics database for New York City. Compares **PostgreSQL** and **MySQL** performance, runs database architecture experiments, and visualizes results in a **Streamlit** dashboard.

## Technology Stack

- **Backend:** Python 3.11+, `psycopg2`, `mysql-connector-python`, `pandas`, `numpy`, `concurrent.futures`
- **Frontend:** Streamlit, Plotly
- **Containers:** Docker, Docker Compose

## Project Structure

```
NYC-Traffic-Congestion/
├── database/
│   ├── postgres_schema.sql
│   └── mysql_schema.sql
├── data_loader/
│   └── load_data.py
├── backend/
│   ├── db_connections.py
│   ├── queries.py
│   ├── benchmark_runner.py
│   ├── epoch_timestamp_test.py
│   ├── index_structure_test.py
│   ├── concurrency_test.py
│   └── planner_analysis.py
├── frontend/
│   └── dashboard.py
├── data/
│   └── benchmark_results.csv
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
└── README.md
```

## Database Setup

From the project root, after PostgreSQL and MySQL are running (e.g. via Docker Compose):

**PostgreSQL:**

```bash
psql -U postgres -h localhost -d benchmark_pg -f database/postgres_schema.sql
```

**MySQL:**

```bash
mysql -u root -proot -h 127.0.0.1 benchmark_mysql < database/mysql_schema.sql
```

Inside Docker network (from `app` service), use hostnames `postgres` and `mysql` and the same credentials.

## Running the System

From the project root:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Then open the dashboard at **http://localhost:8501**.

## Dashboard

- **Database Overview** — PostgreSQL and MySQL configuration summary
- **Run Benchmark** — Execute full query benchmark suite (5 runs per query, results appended to CSV)
- **Query Performance Comparison** — Bar charts and table of execution times by query and database
- **Epoch vs Timestamp Benchmark** — PostgreSQL-only time-filtering comparison
- **Index Architecture Benchmark** — PG heap+index vs MySQL clustered index (e.g. `vehicle_class_id = 1`)
- **Concurrency Benchmark** — 10 / 50 / 100 concurrent queries; QPS and average latency
- **Query Planner Output** — PostgreSQL `EXPLAIN ANALYZE` (planning time, execution time, join algorithms)

## Local Development (without Docker)

1. Install Python 3.11+ and create a virtualenv.
2. `pip install -r requirements.txt`
3. Run PostgreSQL and MySQL locally; point `backend/db_connections.py` to `host=localhost` (or your hosts).
4. Apply schema scripts, then optionally: `python data_loader/load_data.py`
5. Run dashboard: `PYTHONPATH=. streamlit run frontend/dashboard.py`

## Version Control

Commits are split by: project structure → database scripts → backend → frontend → Docker and docs.
