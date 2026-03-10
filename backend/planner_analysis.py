"""
PostgreSQL query planner analysis: run EXPLAIN ANALYZE and extract
planning time, execution time, and join algorithm.
"""
import re
from backend.db_connections import get_postgres_connection
from backend.queries import QUERY_JOIN, QUERY_AGGREGATION, QUERY_INDEX_LOOKUP


def run_explain_analyze(query: str) -> str:
    """Run EXPLAIN (ANALYZE, FORMAT TEXT) and return the plan text."""
    conn = get_postgres_connection()
    try:
        cur = conn.cursor()
        cur.execute("EXPLAIN (ANALYZE, FORMAT TEXT) " + query)
        rows = cur.fetchall()
        return "\n".join(r[0] for r in rows)
    finally:
        conn.close()


def parse_planning_time(plan_text: str) -> float | None:
    """Extract planning time in ms from plan output."""
    m = re.search(r"Planning Time:\s*([\d.]+)\s*ms", plan_text)
    return float(m.group(1)) if m else None


def parse_execution_time(plan_text: str) -> float | None:
    """Extract execution time in ms from plan output."""
    m = re.search(r"Execution Time:\s*([\d.]+)\s*ms", plan_text)
    return float(m.group(1)) if m else None


def parse_join_algorithms(plan_text: str) -> list[str]:
    """Extract join node types (e.g. Hash Join, Nested Loop)."""
    joins = re.findall(r"(\w+ Join)", plan_text, re.IGNORECASE)
    return list(dict.fromkeys(joins))  # unique, order preserved


def analyze_query(name: str, query: str) -> dict:
    """Run EXPLAIN ANALYZE and return structured result."""
    plan_text = run_explain_analyze(query)
    return {
        "query_name": name,
        "planning_time_ms": parse_planning_time(plan_text),
        "execution_time_ms": parse_execution_time(plan_text),
        "join_algorithms": parse_join_algorithms(plan_text),
        "plan_text": plan_text,
    }


def run_planner_analysis() -> list[dict]:
    """Run planner analysis on key benchmark queries."""
    queries = [
        ("aggregation", QUERY_AGGREGATION),
        ("join", QUERY_JOIN),
        ("index_lookup", QUERY_INDEX_LOOKUP),
    ]
    return [analyze_query(name, q) for name, q in queries]
