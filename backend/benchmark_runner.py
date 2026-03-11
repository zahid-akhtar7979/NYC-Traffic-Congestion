"""
Benchmark runner: executes queries on PostgreSQL and MySQL,
repeats each query 5 times with one warm-up run, computes average execution time.
Results are saved to data/benchmark_results.csv.
"""
import os
import sys
import time
import csv
from datetime import datetime

# Ensure project root is on path when run as script
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.db_connections import get_postgres_connection, get_mysql_connection
from backend.queries import BENCHMARK_QUERIES


NUM_WARMUP = 1
NUM_RUNS = 5
RESULTS_PATH = "data/benchmark_results.csv"
RESULTS_HEADER = [
    "database_name",
    "query_name",
    "benchmark_type",
    "execution_time_ms",
    "rows_returned",
    "timestamp",
]


def run_query_pg(query: str):
    """Execute query on PostgreSQL; return (rows, elapsed_ms)."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        start = time.perf_counter()
        cur.execute(query)
        rows = cur.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return len(rows), elapsed_ms
    finally:
        conn.close()


def run_query_mysql(query: str):
    """Execute query on MySQL; return (rows, elapsed_ms)."""
    conn = get_mysql_connection()
    try:
        cur = conn.cursor()
        start = time.perf_counter()
        cur.execute(query)
        rows = cur.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return len(rows), elapsed_ms
    finally:
        conn.close()


def run_benchmark_single(db_name: str, query_name: str, query: str, run_query):
    """One warm-up, then NUM_RUNS timed runs; return average ms and row count."""
    # Warm-up
    try:
        run_query(query)
    except Exception:
        return None, None
    # Timed runs
    times_ms = []
    row_count = None
    for _ in range(NUM_RUNS):
        try:
            n, t = run_query(query)
            times_ms.append(t)
            if row_count is None:
                row_count = n
        except Exception:
            return None, None
    avg_ms = sum(times_ms) / len(times_ms) if times_ms else None
    return avg_ms, row_count


def run_all_benchmarks(append: bool = True) -> list[dict]:
    """Run all benchmark queries on PostgreSQL and MySQL; append results to CSV."""
    os.makedirs(os.path.dirname(RESULTS_PATH) or ".", exist_ok=True)
    file_exists = os.path.isfile(RESULTS_PATH)
    results = []
    ts = datetime.utcnow().isoformat() + "Z"

    for query_name, query in BENCHMARK_QUERIES.items():
        for db_name, run_fn in [
            ("postgres", lambda q=query: run_query_pg(q)),
            ("mysql", lambda q=query: run_query_mysql(q)),
        ]:
            avg_ms, rows = run_benchmark_single(db_name, query_name, query, run_fn)
            row = {
                "database_name": db_name,
                "query_name": query_name,
                "benchmark_type": "query_performance",
                "execution_time_ms": round(avg_ms, 4) if avg_ms is not None else "",
                "rows_returned": rows if rows is not None else "",
                "timestamp": ts,
            }
            results.append(row)

    with open(RESULTS_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULTS_HEADER)
        if not file_exists or not append:
            w.writeheader()
        for r in results:
            w.writerow(r)

    return results
