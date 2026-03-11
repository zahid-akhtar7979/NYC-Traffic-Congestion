"""
Extended benchmark suite matching the comparison report categories:
Simple Filter, GROUP BY (daily CRZ, mode+month ridership), 3-Table JOIN,
Date Range 30-day, Window Function (LAG/rolling avg), CTE, Index Impact, Data Ingestion.
Returns execution times in seconds for MySQL and PostgreSQL.
"""
import os
import sys
import time
import random

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.db_connections import get_postgres_connection, get_mysql_connection

NUM_RUNS = 3
NUM_WARMUP = 1
INGESTION_ROWS = 50_000
ID_OFFSET = 3_000_000  # avoid PK collision with main data


def _run_pg(query: str) -> float:
    """Execute on PostgreSQL; return elapsed seconds."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        for _ in range(NUM_WARMUP):
            cur.execute(query)
            cur.fetchall()
        start = time.perf_counter()
        for _ in range(NUM_RUNS):
            cur.execute(query)
            cur.fetchall()
        return (time.perf_counter() - start) / NUM_RUNS
    finally:
        conn.close()


def _run_mysql(query: str) -> float:
    """Execute on MySQL; return elapsed seconds."""
    conn = get_mysql_connection()
    try:
        cur = conn.cursor()
        for _ in range(NUM_WARMUP):
            cur.execute(query)
            cur.fetchall()
        start = time.perf_counter()
        for _ in range(NUM_RUNS):
            cur.execute(query)
            cur.fetchall()
        return (time.perf_counter() - start) / NUM_RUNS
    finally:
        conn.close()


def _ingest_pg(rows: int) -> float:
    """Insert rows into Fact_CRZ_Entries (PostgreSQL); return seconds. Rolls back so no data persists."""
    conn = get_postgres_connection()
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute("SELECT date_id FROM Dim_Date LIMIT 1")
        date_id = cur.fetchone()[0]
        cur.execute("SELECT time_id FROM Dim_Time LIMIT 1")
        time_id = cur.fetchone()[0]
        cur.execute("SELECT location_id FROM Dim_Location LIMIT 1")
        location_id = cur.fetchone()[0]
        cur.execute("SELECT vehicle_class_id FROM Dim_Vehicle_Class LIMIT 3")
        vc_ids = [r[0] for r in cur.fetchall()]
        batch = 5000
        start = time.perf_counter()
        for i in range(0, rows, batch):
            vals = [
                (ID_OFFSET + i + j, date_id, time_id, location_id, random.choice(vc_ids), random.randint(1, 20))
                for j in range(min(batch, rows - i))
            ]
            cur.executemany(
                "INSERT INTO Fact_CRZ_Entries (crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (crz_entry_id) DO NOTHING",
                vals,
            )
        elapsed = time.perf_counter() - start
        conn.rollback()
        return elapsed
    finally:
        conn.close()


def _ingest_mysql(rows: int) -> float:
    """Insert rows into Fact_CRZ_Entries (MySQL); return seconds. Rolls back so no data persists."""
    conn = get_mysql_connection()
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute("SELECT date_id FROM Dim_Date LIMIT 1")
        date_id = cur.fetchone()[0]
        cur.execute("SELECT time_id FROM Dim_Time LIMIT 1")
        time_id = cur.fetchone()[0]
        cur.execute("SELECT location_id FROM Dim_Location LIMIT 1")
        location_id = cur.fetchone()[0]
        cur.execute("SELECT vehicle_class_id FROM Dim_Vehicle_Class LIMIT 3")
        vc_ids = [r[0] for r in cur.fetchall()]
        batch = 5000
        start = time.perf_counter()
        for i in range(0, rows, batch):
            vals = [
                (ID_OFFSET + i + j, date_id, time_id, location_id, random.choice(vc_ids), random.randint(1, 20))
                for j in range(min(batch, rows - i))
            ]
            cur.executemany(
                "INSERT IGNORE INTO Fact_CRZ_Entries (crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count) VALUES (%s, %s, %s, %s, %s, %s)",
                vals,
            )
        elapsed = time.perf_counter() - start
        conn.rollback()
        return elapsed
    finally:
        conn.close()


# Query definitions (SQL, description)
QUERIES = [
    ("simple_filter", "Simple Filter (COUNT, single date)", """
        SELECT COUNT(*) FROM Fact_CRZ_Entries WHERE date_id = 20240101
    """),
    ("groupby_daily_crz", "GROUP BY — daily CRZ aggregation", """
        SELECT date_id, SUM(entry_count) AS total_entries
        FROM Fact_CRZ_Entries
        GROUP BY date_id
    """),
    ("groupby_mode_month_ridership", "GROUP BY — mode + month ridership", """
        SELECT d.year, d.month, tm.transport_mode_name, SUM(r.ridership_count) AS total
        FROM Fact_Ridership r
        JOIN Dim_Date d ON r.date_id = d.date_id
        JOIN Dim_Transport_Mode tm ON r.transport_mode_id = tm.transport_mode_id
        GROUP BY d.year, d.month, tm.transport_mode_name
    """),
    ("join_3table", "3-Table JOIN (date + location/borough)", """
        SELECT l.borough, d.year, d.month, COUNT(*) AS entry_count, SUM(f.entry_count) AS total_entries
        FROM Fact_CRZ_Entries f
        JOIN Dim_Date d ON f.date_id = d.date_id
        JOIN Dim_Location l ON f.location_id = l.location_id
        GROUP BY l.borough, d.year, d.month
    """),
    ("date_range_30day", "Date Range Filter — 30-day window", """
        SELECT COUNT(*), SUM(entry_count)
        FROM Fact_CRZ_Entries
        WHERE date_id BETWEEN 20240101 AND 20240130
    """),
    ("window_rolling_7day", "Window Function — 7-day rolling avg (LAG)", """
        WITH daily AS (
            SELECT date_id, SUM(entry_count) AS total
            FROM Fact_CRZ_Entries
            GROUP BY date_id
        )
        SELECT date_id, total,
               AVG(total) OVER (ORDER BY date_id ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7
        FROM daily
    """),
    ("cte_top_vehicle_class_per_month", "CTE — top vehicle class per month", """
        WITH monthly AS (
            SELECT d.year, d.month, f.vehicle_class_id, SUM(f.entry_count) AS total
            FROM Fact_CRZ_Entries f
            JOIN Dim_Date d ON f.date_id = d.date_id
            GROUP BY d.year, d.month, f.vehicle_class_id
        ),
        ranked AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY year, month ORDER BY total DESC) AS rn
            FROM monthly
        )
        SELECT * FROM ranked WHERE rn = 1
    """),
]

# Index impact: two queries (with index = vehicle_class_id; without = full scan via entry_count)
INDEX_WITH = "SELECT COUNT(*), SUM(entry_count) FROM Fact_CRZ_Entries WHERE vehicle_class_id = 1"
INDEX_WITHOUT = "SELECT COUNT(*), SUM(entry_count) FROM Fact_CRZ_Entries WHERE entry_count > 0"


def _sec_to_ms(sec: float) -> float:
    """Convert seconds to milliseconds; round to 1 decimal."""
    if sec is None:
        return None
    return round(sec * 1000, 1)


def run_extended_benchmarks(include_ingestion: bool = True) -> dict:
    """Run all extended benchmarks. Query times returned in ms; ingestion in seconds."""
    results = {}
    for qkey, label, sql in QUERIES:
        sql = sql.strip()
        try:
            pg_sec = _run_pg(sql)
        except Exception:
            pg_sec = None
        try:
            my_sec = _run_mysql(sql)
        except Exception:
            my_sec = None
        results[label] = {
            "postgres": _sec_to_ms(pg_sec),
            "mysql": _sec_to_ms(my_sec),
        }

    # Index impact (report in ms)
    try:
        pg_with = _run_pg(INDEX_WITH)
        pg_without = _run_pg(INDEX_WITHOUT)
        results["Index Impact: WITH vs WITHOUT index"] = {
            "postgres": f"{_sec_to_ms(pg_with)} vs {_sec_to_ms(pg_without)} ms",
            "mysql": None,
        }
    except Exception:
        results["Index Impact: WITH vs WITHOUT index"] = {"postgres": None, "mysql": None}
    try:
        my_with = _run_mysql(INDEX_WITH)
        my_without = _run_mysql(INDEX_WITHOUT)
        results["Index Impact: WITH vs WITHOUT index"]["mysql"] = f"{_sec_to_ms(my_with)} vs {_sec_to_ms(my_without)} ms"
    except Exception:
        pass

    # Data ingestion 50K rows (keep in seconds)
    if include_ingestion:
        try:
            results["Data Ingestion — 50K rows"] = {"postgres": round(_ingest_pg(INGESTION_ROWS), 1), "mysql": None}
        except Exception:
            results["Data Ingestion — 50K rows"] = {"postgres": None, "mysql": None}
        try:
            my_ing = _ingest_mysql(INGESTION_ROWS)
            results["Data Ingestion — 50K rows"]["mysql"] = round(my_ing, 1)
        except Exception:
            results.setdefault("Data Ingestion — 50K rows", {})["mysql"] = None

    return results


def print_report_table(results: dict) -> None:
    """Print markdown table of results. Query times in ms; ingestion in seconds."""
    print("\n| Query Category | MySQL (Relational) | PostgreSQL (Relational) |")
    print("|----------------|--------------------|--------------------------|")
    for label, vals in results.items():
        my = vals.get("mysql")
        pg = vals.get("postgres")
        if my is None:
            my_s = "TBD"
        elif "Data Ingestion" in label:
            my_s = f"{my} s"
        elif isinstance(my, str):
            my_s = my
        else:
            my_s = f"{my} ms"
        if pg is None:
            pg_s = "TBD"
        elif "Data Ingestion" in label:
            pg_s = f"{pg} s"
        elif isinstance(pg, str):
            pg_s = pg
        else:
            pg_s = f"{pg} ms"
        print(f"| {label} | {my_s} | {pg_s} |")


if __name__ == "__main__":
    print("Running extended benchmark suite...")
    res = run_extended_benchmarks(include_ingestion=True)
    print_report_table(res)
    # Also write JSON for report generation
    import json
    out_path = os.path.join(_root, "data", "extended_benchmark_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(res, f, indent=2)
    print(f"\nResults saved to {out_path}")
