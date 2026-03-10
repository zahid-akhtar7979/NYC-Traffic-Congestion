"""
Concurrency benchmark using ThreadPoolExecutor.
Runs 10, 50, and 100 concurrent queries; measures queries per second and average latency.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.db_connections import get_postgres_connection, get_mysql_connection
from backend.queries import QUERY_INDEX_LOOKUP


def run_one_query_pg():
    """Execute one query on PostgreSQL; return latency in seconds."""
    start = time.perf_counter()
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        cur.execute(QUERY_INDEX_LOOKUP)
        cur.fetchall()
        return time.perf_counter() - start
    finally:
        conn.close()


def run_one_query_mysql():
    """Execute one query on MySQL; return latency in seconds."""
    start = time.perf_counter()
    conn = get_mysql_connection()
    try:
        cur = conn.cursor()
        cur.execute(QUERY_INDEX_LOOKUP)
        cur.fetchall()
        return time.perf_counter() - start
    finally:
        conn.close()


def run_concurrent(connection_count: int, run_one_query) -> dict:
    """Run connection_count queries concurrently; return qps and avg latency (ms)."""
    start = time.perf_counter()
    latencies = []
    with ThreadPoolExecutor(max_workers=connection_count) as executor:
        futures = [executor.submit(run_one_query) for _ in range(connection_count)]
        for f in as_completed(futures):
            try:
                latencies.append(f.result())
            except Exception:
                pass
    elapsed = time.perf_counter() - start
    qps = len(latencies) / elapsed if elapsed > 0 else 0
    avg_latency_ms = (sum(latencies) / len(latencies)) * 1000 if latencies else 0
    return {
        "concurrent_queries": connection_count,
        "queries_per_second": round(qps, 2),
        "average_latency_ms": round(avg_latency_ms, 4),
        "completed": len(latencies),
    }


def run_concurrency_benchmark() -> dict:
    """Run 10, 50, 100 concurrent queries on both PostgreSQL and MySQL."""
    levels = [10, 50, 100]
    results = {"postgres": [], "mysql": []}
    for n in levels:
        results["postgres"].append(
            {"concurrent_queries": n, **run_concurrent(n, run_one_query_pg)}
        )
        results["mysql"].append(
            {"concurrent_queries": n, **run_concurrent(n, run_one_query_mysql)}
        )
    return results
