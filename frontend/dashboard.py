"""
Streamlit dashboard for NYC Congestion Pricing Analytics benchmarks.
Sections: Database Overview, Run Benchmark, Query Performance, Epoch vs Timestamp,
Index Architecture, Concurrency Results, Query Planner Output.
"""
import os
import sys
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Project root on path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.benchmark_runner import run_all_benchmarks
from backend.epoch_timestamp_test import run_epoch_timestamp_benchmark
from backend.index_structure_test import run_index_structure_benchmark
from backend.concurrency_test import run_concurrency_benchmark
from backend.planner_analysis import run_planner_analysis

RESULTS_PATH = os.path.join(_root, "data", "benchmark_results.csv")
st.set_page_config(page_title="NYC Traffic Congestion Benchmark", layout="wide")

st.title("NYC Congestion Pricing Analytics — Benchmark Dashboard")

# --- Database Overview ---
st.header("Database Overview")
col1, col2 = st.columns(2)
with col1:
    st.subheader("PostgreSQL")
    st.markdown("""
    - **Host:** postgres (Docker)
    - **Database:** benchmark_pg
    - **Schema:** Star schema (dimensions + facts)
    - **Fact tables:** Fact_CRZ_Entries, Fact_Bridge_Tunnel_Crossings, Fact_Ridership, Fact_Fare_Evasion, Fact_Traffic_Violation
    """)
with col2:
    st.subheader("MySQL")
    st.markdown("""
    - **Host:** mysql (Docker)
    - **Database:** benchmark_mysql
    - **Schema:** Same star schema (MySQL-compatible)
    - **Engine:** InnoDB, foreign keys and indexes
    """)

# --- Run Benchmark ---
st.header("Run Benchmark")
if st.button("Run full benchmark suite"):
    with st.spinner("Running benchmarks (PostgreSQL + MySQL, 5 runs per query)…"):
        try:
            results = run_all_benchmarks(append=True)
            st.success(f"Completed {len(results)} benchmark runs. Results appended to CSV.")
        except Exception as e:
            st.error(str(e))

# --- Query Performance Comparison ---
st.header("Query Performance Comparison")
if os.path.isfile(RESULTS_PATH):
    df = pd.read_csv(RESULTS_PATH)
    if len(df) > 0:
        qpf = df[df["benchmark_type"] == "query_performance"]
        if len(qpf) > 0:
            fig = px.bar(
                qpf,
                x="query_name",
                y="execution_time_ms",
                color="database_name",
                barmode="group",
                title="Average execution time by query and database (ms)",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(qpf, use_container_width=True, hide_index=True)
        else:
            st.info("No query performance rows in CSV yet. Run the benchmark above.")
    else:
        st.info("CSV is empty. Run the benchmark above.")
else:
    st.info("No results file yet. Run the benchmark above.")

# --- Epoch vs Timestamp Benchmark ---
st.header("Epoch vs Timestamp Benchmark (PostgreSQL)")
if st.button("Run Epoch vs Timestamp benchmark"):
    with st.spinner("Running epoch vs timestamp benchmark…"):
        try:
            res = run_epoch_timestamp_benchmark()
            st.session_state["epoch_timestamp"] = res
        except Exception as e:
            st.error(str(e))
if "epoch_timestamp" in st.session_state:
    r = st.session_state["epoch_timestamp"]
    fig = go.Figure(data=[
        go.Bar(name="Timestamp", x=["Avg time"], y=[r["timestamp"]["avg_ms"]]),
        go.Bar(name="Epoch", x=["Avg time"], y=[r["epoch"]["avg_ms"]]),
    ])
    fig.update_layout(title="Time filter: TIMESTAMP vs Epoch (ms)", barmode="group")
    st.plotly_chart(fig, use_container_width=True)
    st.json(r)

# --- Index Architecture Benchmark ---
st.header("Index Architecture Benchmark")
if st.button("Run Index structure benchmark"):
    with st.spinner("Running index benchmark (PG heap+index vs MySQL clustered)…"):
        try:
            res = run_index_structure_benchmark()
            st.session_state["index_bench"] = res
        except Exception as e:
            st.error(str(e))
if "index_bench" in st.session_state:
    r = st.session_state["index_bench"]
    df_idx = pd.DataFrame(r)
    fig = px.bar(
        df_idx,
        x="database",
        y="avg_ms",
        color="architecture",
        title="Index lookup: vehicle_class_id = 1 (avg ms)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_idx, use_container_width=True, hide_index=True)

# --- Concurrency Benchmark Results ---
st.header("Concurrency Benchmark Results")
if st.button("Run Concurrency benchmark"):
    with st.spinner("Running 10 / 50 / 100 concurrent queries…"):
        try:
            res = run_concurrency_benchmark()
            st.session_state["concurrency"] = res
        except Exception as e:
            st.error(str(e))
if "concurrency" in st.session_state:
    r = st.session_state["concurrency"]
    for db in ["postgres", "mysql"]:
        rows = r[db]
        dfc = pd.DataFrame(rows)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=dfc["concurrent_queries"], y=dfc["queries_per_second"], name="QPS"))
        fig.add_trace(go.Scatter(x=dfc["concurrent_queries"], y=dfc["average_latency_ms"], name="Avg latency (ms)", yaxis="y2"))
        fig.update_layout(
            title=f"Concurrency — {db}",
            xaxis_title="Concurrent queries",
            yaxis_title="Queries per second",
            yaxis2=dict(title="Avg latency (ms)", overlaying="y", side="right"),
        )
        st.plotly_chart(fig, use_container_width=True)
    st.json(r)

# --- Query Planner Output ---
st.header("PostgreSQL Query Planner Output")
if st.button("Run Planner analysis (EXPLAIN ANALYZE)"):
    with st.spinner("Running EXPLAIN ANALYZE on sample queries…"):
        try:
            res = run_planner_analysis()
            st.session_state["planner"] = res
        except Exception as e:
            st.error(str(e))
if "planner" in st.session_state:
    for item in st.session_state["planner"]:
        with st.expander(f"Query: {item['query_name']}"):
            st.metric("Planning time (ms)", item.get("planning_time_ms"))
            st.metric("Execution time (ms)", item.get("execution_time_ms"))
            st.write("Join algorithms:", item.get("join_algorithms", []))
            st.text(item.get("plan_text", ""))
