"""
Epoch vs Timestamp benchmark (PostgreSQL only).
Creates events_timestamp and events_epoch tables and runs time-filtering benchmarks.
"""
import time
from backend.db_connections import get_postgres_connection


def setup_epoch_timestamp_tables():
    """Create events_timestamp and events_epoch tables if not exist."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events_timestamp (
                event_id SERIAL PRIMARY KEY,
                event_time TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events_epoch (
                event_id SERIAL PRIMARY KEY,
                event_time_epoch BIGINT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def run_timestamp_filter_benchmark(num_runs: int = 5, warmup: int = 1) -> dict:
    """Benchmark time filtering on events_timestamp (TIMESTAMP column)."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        # Warm-up
        for _ in range(warmup):
            cur.execute("""
                SELECT * FROM events_timestamp
                WHERE event_time BETWEEN '2024-01-01' AND '2024-01-31'
            """)
            cur.fetchall()
        times = []
        for _ in range(num_runs):
            start = time.perf_counter()
            cur.execute("""
                SELECT * FROM events_timestamp
                WHERE event_time BETWEEN '2024-01-01' AND '2024-01-31'
            """)
            cur.fetchall()
            times.append((time.perf_counter() - start) * 1000)
        return {"avg_ms": sum(times) / len(times), "runs": num_runs}
    finally:
        conn.close()


def run_epoch_filter_benchmark(num_runs: int = 5, warmup: int = 1) -> dict:
    """Benchmark time filtering on events_epoch (BIGINT epoch column)."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        # 2024-01-01 to 2024-01-31 in Unix epoch seconds
        start_epoch = 1704067200  # 2024-01-01 00:00:00 UTC
        end_epoch = 1706745599    # 2024-01-31 23:59:59 UTC
        for _ in range(warmup):
            cur.execute("""
                SELECT * FROM events_epoch
                WHERE event_time_epoch BETWEEN %s AND %s
            """, (start_epoch, end_epoch))
            cur.fetchall()
        times = []
        for _ in range(num_runs):
            start = time.perf_counter()
            cur.execute("""
                SELECT * FROM events_epoch
                WHERE event_time_epoch BETWEEN %s AND %s
            """, (start_epoch, end_epoch))
            cur.fetchall()
            times.append((time.perf_counter() - start) * 1000)
        return {"avg_ms": sum(times) / len(times), "runs": num_runs}
    finally:
        conn.close()


def run_epoch_timestamp_benchmark() -> dict:
    """Setup tables, run both benchmarks, return results."""
    setup_epoch_timestamp_tables()
    return {
        "timestamp": run_timestamp_filter_benchmark(),
        "epoch": run_epoch_filter_benchmark(),
    }
