# Benchmark Comparison Report: MySQL vs PostgreSQL

**NYC Congestion Pricing Analytics — Relational Database Performance**  
*Same star schema and data (~1M Fact_CRZ_Entries, ~100K Fact_Ridership).*

**Units:** Query execution times are in **milliseconds (ms)**. Data ingestion is in **seconds (s)**. This avoids misleading "0.00" values: fast queries (e.g. indexed COUNT) show as a few ms instead of 0.00 s.

---

## Summary Table

**Units:** Query times = **milliseconds (ms)**. Ingestion = **seconds (s)**.

| Query Category | MySQL (Relational) | PostgreSQL (Relational) |
|----------------|--------------------|--------------------------|
| Simple Filter (COUNT, single date) | 2.5 ms | 1.8 ms |
| GROUP BY — daily CRZ aggregation | 470.0 ms | 20.0 ms |
| GROUP BY — mode + month ridership | 100.0 ms | 20.0 ms |
| 3-Table JOIN (date + location/borough) | 760.0 ms | 60.0 ms |
| Date Range Filter — 30-day window | 3.2 ms | 2.1 ms |
| Window Function — 7-day rolling avg (LAG) | 480.0 ms | 20.0 ms |
| CTE — top vehicle class per month | 260.0 ms | 40.0 ms |
| Index Impact: WITH vs WITHOUT index | 100 vs 100 ms | 5 vs 8 ms |
| Data Ingestion — 50K rows | 0.4 s | 2.8 s |

*Values above use the **ms/s** reporting from the extended benchmark (query times in milliseconds so fast runs are not shown as "0.00"). Re-run the benchmark to refresh with your environment:*

```bash
docker compose -f docker/docker-compose.yml run --rm app python backend/extended_benchmark.py
```

---

## Findings

### 1. **Simple Filter & Date Range**
- Both engines complete single-date COUNT and 30-day range filters in a few milliseconds.
- Indexes on `date_id` (e.g. `idx_crz_date`) keep these operations fast; reporting in **ms** avoids misleading "0.00 s".

### 2. **GROUP BY (daily CRZ; mode + month ridership)**
- **PostgreSQL** is faster (e.g. 20 ms vs 470 ms and 100 ms for MySQL).
- GROUP BY over fact tables with joins to dimensions is a common analytics pattern; PostgreSQL’s planner and aggregation show an advantage here.

### 3. **3-Table JOIN (date + location/borough)**
- **PostgreSQL** again faster (e.g. 60 ms vs 760 ms).
- Join order and hash vs nested-loop strategies differ between engines; the star schema suits PostgreSQL’s join handling in this workload.

### 4. **Window Function (7-day rolling avg)**
- **PostgreSQL** much faster (e.g. 20 ms vs 480 ms).
- Window functions (LAG, AVG OVER) are well optimized in PostgreSQL for analytics.

### 5. **CTE — top vehicle class per month**
- **PostgreSQL** faster (e.g. 40 ms vs 260 ms).
- CTEs and ROW_NUMBER() are executed efficiently by PostgreSQL’s planner.

### 6. **Index Impact (WITH vs WITHOUT index)**
- Reported as "X vs Y ms" (with index vs without). On larger data or cold cache, the gap between indexed and full-scan is more pronounced (e.g. 2.1 vs 38.7 s for MySQL in other runs).

### 7. **Data Ingestion — 50K rows**
- **MySQL** was faster for batch insert in this run (~0.4 s vs ~2.8 s).
- Inserts were run in a single transaction and then rolled back so no test data persists. MySQL’s InnoDB bulk-insert path can be very efficient for batched, transactional inserts.

---

## How to Reproduce

From the project root with Docker stack up:

```bash
docker compose -f docker/docker-compose.yml run --rm app python backend/extended_benchmark.py
```

The script prints the comparison table and writes `data/extended_benchmark_results.json`. Re-run after schema or data changes to refresh numbers.

---

## Notes

- **Data volume:** This run used the project’s standard load (~1M CRZ rows, ~100K ridership). Larger or smaller data will change absolute times; relative ordering (e.g. PostgreSQL faster for GROUP BY / JOIN / window) may hold.
- **Index impact:** For a more dramatic “with vs without index” comparison, use a larger table or disable indexes temporarily on the filter column.
- **Ingestion:** The 50K-row ingestion test rolls back the transaction so the database is unchanged after the run.
