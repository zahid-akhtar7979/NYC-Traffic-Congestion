# NYC Congestion Pricing Analytics — Project Report

**Benchmarking System: Design, Findings, Challenges & Recommendations**

---

## Table of Contents

1. [Findings & Design Alignment](#1-findings--design-alignment)  
2. [Tool Rationale & Expectations](#2-tool-rationale--expectations)  
3. [Challenges & Resolutions](#3-challenges--resolutions)  
4. [Recommendations](#4-recommendations)  

---

## 1. Findings & Design Alignment

### 1.1 Design and Analysis Phase Intent

The project was conceived to build a **benchmarking system** for a congestion-pricing analytics workload over a **star schema**: dimension tables (Date, Time, Location, Vehicle Class, etc.) and fact tables (CRZ Entries, Ridership, Bridge/Tunnel Crossings, Fare Evasion, Traffic Violations). The goals were to:

- Compare **PostgreSQL** and **MySQL** on the same workload.
- Measure **query performance** (aggregation, joins, range filters, index lookups).
- Explore **epoch vs timestamp** storage for time filtering (PostgreSQL).
- Compare **index architecture** (heap + B-tree vs clustered index).
- Stress-test **concurrency** (10, 50, 100 concurrent queries).
- Inspect **PostgreSQL query planner** behavior (EXPLAIN ANALYZE).

### 1.2 Findings Summary

| Area | Finding | Alignment with Design |
|------|---------|------------------------|
| **Query performance** | Both databases handle the star-schema workload; join and aggregation times scale with data volume. Indexed lookups (e.g. `vehicle_class_id = 1`) benefit from indexes on fact tables. | Aligned: we measure exactly these query families and can compare PG vs MySQL side by side. |
| **Epoch vs timestamp** | For time-range filters, TIMESTAMP and BIGINT epoch storage show similar performance at moderate scale; epoch can simplify application logic and portability. | Aligned: experiment is implemented and visualized; findings inform storage choices. |
| **Index architecture** | PostgreSQL’s heap + secondary index vs MySQL’s clustered/secondary index yield different access patterns; index lookup benchmarks surface these differences. | Aligned: dedicated benchmark and dashboard section. |
| **Concurrency** | Throughput (QPS) and latency under 10/50/100 concurrent queries reveal how each engine handles connection and lock contention. | Aligned: ThreadPoolExecutor-based tests and dashboard charts. |
| **Query planner** | PostgreSQL’s EXPLAIN ANALYZE exposes planning time, execution time, and join algorithms (e.g. Hash Join, Nested Loop), supporting tuning and education. | Aligned: planner analysis module and expandable dashboard output. |
| **Data pipeline** | NYC Open Data (CRZ entries, ridership, subway entrances) maps cleanly to the star schema; synthetic expansion to ~1M CRZ and ~100K ridership makes benchmarks meaningful. | Aligned: design assumed realistic data volume; loader delivers it. |

### 1.3 Alignment Verdict

The implemented system **matches the design and analysis phase**: same schema (dimensions + facts), same workload categories, same experiments (query performance, epoch/timestamp, index structure, concurrency, planner), and a single dashboard to run experiments and view results. Findings are therefore directly comparable to what was originally scoped.

---

## 2. Tool Rationale & Expectations

### 2.1 Why These Tools?

| Choice | Rationale | Expected vs Discovered |
|--------|-----------|------------------------|
| **PostgreSQL 15** | Strong analytics support, mature optimizer, EXPLAIN ANALYZE, and common choice for data warehouses and reporting. | As expected: predictable plans, good join performance, and rich planner output. |
| **MySQL 8** | Widely used, InnoDB clustered indexes, different locking and execution model; provides a real-world contrast to PostgreSQL. | As expected: comparable on simple lookups; different behavior under concurrency and complex joins. |
| **Star schema (Dim_* / Fact_*)** | Standard for analytics: clear separation of dimensions and measures, simple joins, and easy to explain and maintain. | As expected: queries are readable and map well to business questions (e.g. entries by vehicle class, by date). |
| **Python 3.11+** | Single language for ETL, benchmarking, and dashboard; good drivers for both databases and rich data ecosystem. | As expected: one codebase for runner, loader, and app; minimal context switching. |
| **Streamlit + Plotly** | Fast to build interactive dashboards; Plotly gives publication-quality charts without heavy front-end work. | As expected: quick iteration on charts and tables; suitable for demos and reports. |
| **Docker Compose** | Reproducible environment: same PG/MySQL versions and app runtime everywhere; no “works on my machine” for DB setup. | As expected: one command to bring up DBs and app; same behavior locally and in CI. |
| **NYC Open Data + synthetic scaling** | Realistic domain (congestion, ridership) and controllable volume; synthetic expansion ensures benchmarks run at meaningful scale. | As expected: real column semantics; ~1M/100K rows make timing and planner differences visible. |
| **Batch inserts (e.g. 10K rows/commit)** | Reduces round-trips and transaction overhead during bulk load. | As expected: load completes in reasonable time; optional ANALYZE/VACUUM after load improves plan quality. |

### 2.2 What We Discovered in Practice

- **Dual-database support** required careful handling of connection config (Docker hostnames vs Railway env vars); a small abstraction in `db_connections.py` keeps the rest of the code agnostic.
- **CSV result format** (e.g. `benchmark_results.csv`) is sufficient for the dashboard and keeps the system simple; for long-term use, appending runs and preserving history could be improved (see Recommendations).
- **Chart design** matters: labeling by workload/query and coloring by database (PostgreSQL vs MySQL) avoids mixing “query name,” “description,” and “database” in one legend and keeps the report readable and academic.

---

## 3. Challenges & Resolutions

### 3.1 Schema and Data

| Challenge | Resolution |
|-----------|------------|
| **“Relation already exists” / “Table already exists”** when re-running schema scripts | Schema application is a **one-time** step. Scripts were split: `init_db_and_data.sh` (build + schema + load) for first run; `start_stack.sh` only starts containers. Users run init once, then use start for daily use. |
| **Primary key / column mismatches** (e.g. `entry_id` vs `crz_entry_id`) | Queries and schema were aligned to the actual star schema: fact tables use `crz_entry_id`, `ridership_fact_id`, etc. No synthetic columns were introduced. |
| **MySQL BOOLEAN vs TINYINT** | MySQL schema uses `TINYINT(1)` for flags (e.g. `entry_allowed`, `exit_allowed`) in `Dim_Entrance`; PostgreSQL keeps BOOLEAN. Both schemas stay idiomatic. |

### 3.2 Benchmark Runner & Dashboard

| Challenge | Resolution |
|-----------|------------|
| **“String indices must be integers, not 'str'”** | `BENCHMARK_QUERIES` was sometimes a dict of **strings** (query name → SQL). The runner was written to expect a dict of **dicts** (with `"sql"`, `"description"`, etc.). The runner was reverted to iterate over `(query_name, query)` where `query` is the raw SQL string, so it works with both the simple and the extended metadata format. |
| **Only one database shown in Query Performance chart** | (1) Ensure both PostgreSQL and MySQL runs write to the CSV (no silent failures). (2) Chart must color by `database_name` and group by query/workload so both DBs appear side by side. (3) Rebuilding the app image after code changes ensures the dashboard uses the latest chart logic. |
| **Legend showing long descriptions instead of database names** | Chart was updated so the legend encodes **database** (PostgreSQL / MySQL) only; query/workload appears on the x-axis and in hover text, keeping the report clean and academic. |

### 3.3 Data Loader & Environment

| Challenge | Resolution |
|-----------|------------|
| **NYC Open Data API limits or 403** | Download uses retries and fallback URLs (e.g. `rows.csv?accessType=DOWNLOAD`). If all fail, the loader falls back to **synthetic data** (same schema, randomized values) so the pipeline and benchmarks still run. |
| **MySQL “Unread result found” after ANALYZE** | MySQL connector requires consuming result sets before committing. After `ANALYZE TABLE`, the code calls `cur.fetchall()` (or equivalent) before `conn.commit()` so no unread result remains. |
| **Different DB hosts locally vs cloud** | `db_connections.py` reads environment variables (e.g. `DATABASE_URL`, `MYSQLHOST`, `MYSQLPORT`) when set; otherwise it uses Docker defaults (`postgres`, `mysql`). Same code works locally and on Railway or similar. |

### 3.4 Operational

| Challenge | Resolution |
|-----------|------------|
| **Re-running schema and data on every “full stack” run** | Separation of scripts: **one-time** `init_db_and_data.sh` (schema + load) vs **every time** `start_stack.sh` (containers only). Documentation and script comments explain when to use each. |

---

## 4. Recommendations

### 4.1 For This Project

- **Benchmark result persistence**  
  Store results in a database table (or append to a versioned CSV) with run id and timestamp so you can compare runs over time and avoid losing history on container rebuilds.

- **Optional benchmark subset**  
  Allow running a subset of queries (e.g. only “OLAP” or only “index lookup”) to shorten feedback loops during tuning.

- **Health checks before benchmark**  
  Verify connectivity to both PostgreSQL and MySQL before starting the suite; fail fast with a clear message if one DB is down.

- **Schema idempotency**  
  Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` (where supported) so re-running the schema script is safe and does not flood logs with “already exists” errors.

- **Dashboard: export and report**  
  Add a “Download report” (PDF or HTML) that includes the current charts and a summary table so the same view can be shared or archived.

### 4.2 For Similar Systems

- **Align schema and query catalog early**  
  Define the star schema and the exact query set (with names and descriptions) in the design phase; it reduces rework when wiring the runner and the dashboard.

- **Unify benchmark result schema**  
  Use a single result format (e.g. database_name, query_name, execution_time_ms, rows_returned, timestamp, optional metadata) from day one so the dashboard and any future tooling stay compatible.

- **Separate one-time vs repeated steps**  
  Document and script “init” (schema, seed data) separately from “run” (start services, run app). It avoids accidental re-loads and makes production and CI clearer.

- **Environment-aware configuration**  
  Keep DB connection logic in one place and drive it with env vars (local, Docker, cloud); the rest of the app stays agnostic and testable.

---

## Document Info

- **Project:** NYC Traffic Congestion — Benchmarking Application  
- **Scope:** Design alignment, findings, tool rationale, challenges, and recommendations  
- **Audience:** Stakeholders, maintainers, and future contributors  

For setup and usage, see the main [README](../README.md) and [Railway Deployment](RAILWAY_DEPLOYMENT.md) (if applicable).
