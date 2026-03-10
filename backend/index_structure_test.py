"""
Index architecture benchmark: compare MySQL clustered index vs PostgreSQL heap + index.
Query: SELECT * FROM Fact_CRZ_Entries WHERE vehicle_class_id = 1
"""
import time
from backend.db_connections import get_postgres_connection, get_mysql_connection
from backend.queries import QUERY_INDEX_LOOKUP

NUM_WARMUP = 1
NUM_RUNS = 5


def run_index_benchmark_pg() -> dict:
    """PostgreSQL: heap + B-tree index on vehicle_class_id."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        for _ in range(NUM_WARMUP):
            cur.execute(QUERY_INDEX_LOOKUP)
            cur.fetchall()
        times = []
        for _ in range(NUM_RUNS):
            start = time.perf_counter()
            cur.execute(QUERY_INDEX_LOOKUP)
            cur.fetchall()
            times.append((time.perf_counter() - start) * 1000)
        return {
            "database": "postgres",
            "architecture": "heap_plus_index",
            "avg_ms": sum(times) / len(times),
            "runs": NUM_RUNS,
        }
    finally:
        conn.close()


def run_index_benchmark_mysql() -> dict:
    """MySQL: clustered primary key / secondary index on vehicle_class_id."""
    conn = get_mysql_connection()
    try:
        cur = conn.cursor()
        for _ in range(NUM_WARMUP):
            cur.execute(QUERY_INDEX_LOOKUP)
            cur.fetchall()
        times = []
        for _ in range(NUM_RUNS):
            start = time.perf_counter()
            cur.execute(QUERY_INDEX_LOOKUP)
            cur.fetchall()
            times.append((time.perf_counter() - start) * 1000)
        return {
            "database": "mysql",
            "architecture": "clustered_index",
            "avg_ms": sum(times) / len(times),
            "runs": NUM_RUNS,
        }
    finally:
        conn.close()


def run_index_structure_benchmark() -> list[dict]:
    """Run index benchmark on both databases."""
    return [run_index_benchmark_pg(), run_index_benchmark_mysql()]
