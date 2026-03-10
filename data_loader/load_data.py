"""
NYC Congestion Pricing Analytics — Data loader.
Downloads NYC Open Data, cleans and normalizes, expands to ~1M CRZ and ~100K ridership,
then batch-inserts into PostgreSQL and/or MySQL. Schema must already be applied.
Run: python data_loader/load_data.py
"""
import logging
import os
import sys
import time
from datetime import datetime

# Project root on path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

import pandas as pd

from backend.db_connections import get_postgres_connection, get_mysql_connection
from data_loader.dataset_ingestion import fetch_all_datasets
from data_loader.data_cleaning import clean_crz, clean_ridership, clean_station_entrances
from data_loader.synthetic_generator import (
    TARGET_CRZ_ROWS,
    TARGET_RIDERSHIP_ROWS,
    expand_crz_to_target,
    expand_ridership_to_target,
)
from data_loader.insert_pipeline import (
    detect_databases,
    build_dimension_lookups,
    insert_dimensions_pg,
    insert_dimensions_mysql,
    insert_fact_crz_pg,
    insert_fact_crz_mysql,
    insert_fact_ridership_pg,
    insert_fact_ridership_mysql,
    run_analyze_pg,
    run_analyze_mysql,
)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _make_fallback_crz(rows: int = TARGET_CRZ_ROWS) -> pd.DataFrame:
    """Generate minimal synthetic CRZ data when download fails."""
    log.warning("Using fallback synthetic CRZ data (%s rows)", rows)
    import numpy as np
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame({
        "toll_date": rng.choice(dates, size=rows),
        "hour_of_day": rng.integers(0, 24, size=rows),
        "vehicle_class": rng.choice(["Passenger", "Truck", "Motorcycle"], size=rows),
        "detection_region": rng.choice(["Manhattan", "Brooklyn", "Queens"], size=rows),
        "crz_entries": np.maximum(1, rng.integers(1, 50, size=rows)),
    })


def _make_fallback_ridership(rows: int = TARGET_RIDERSHIP_ROWS) -> pd.DataFrame:
    """Generate minimal synthetic ridership when download fails."""
    log.warning("Using fallback synthetic ridership (%s rows)", rows)
    import numpy as np
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", "2024-06-30", freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame({
        "date": rng.choice(dates, size=rows),
        "mode": rng.choice(["Subway", "Bus", "LIRR"], size=rows),
        "count": np.maximum(0, rng.integers(1000, 50000, size=rows)),
    })


def _make_fallback_entrances() -> pd.DataFrame:
    """Minimal station/entrance fallback."""
    log.warning("Using fallback synthetic station/entrance data")
    return pd.DataFrame({
        "stop_name": ["34 St-Penn Station", "Grand Central", "Times Sq-42 St"],
        "borough": ["Manhattan", "Manhattan", "Manhattan"],
        "entrance_latitude": [40.7506, 40.7527, 40.7559],
        "entrance_longitude": [-73.9935, -73.9772, -73.9862],
        "entrance_type": ["Stair", "Elevator", "Stair"],
        "line": ["1,2,3", "4,5,6", "1,2,3"],
    })


def load_all(
    target_crz_rows: int = TARGET_CRZ_ROWS,
    target_ridership_rows: int = TARGET_RIDERSHIP_ROWS,
    chunk_size: int = 50_000,
    use_download: bool = True,
) -> dict:
    """
    Download (or use fallback), clean, expand, and insert into database(s).
    Returns stats dict: tables with row counts, total time, insert speed.
    """
    start_total = time.perf_counter()
    stats = {"tables": {}, "total_seconds": 0, "total_rows_inserted": 0, "errors": []}

    # --- 1. Dataset ingestion ---
    log.info("Step 1: Dataset ingestion")
    try:
        if use_download:
            crz_raw, ridership_raw, entrances_raw = fetch_all_datasets(chunk_size=chunk_size)
            log.info("Downloaded CRZ=%s, Ridership=%s, Entrances=%s rows",
                     len(crz_raw), len(ridership_raw), len(entrances_raw))
        else:
            raise RuntimeError("Skip download")
    except Exception as e:
        log.exception("Dataset download failed: %s", e)
        stats["errors"].append(("download", str(e)))
        crz_raw = _make_fallback_crz(min(10_000, target_crz_rows))
        ridership_raw = _make_fallback_ridership(min(5_000, target_ridership_rows))
        entrances_raw = _make_fallback_entrances()
        log.info("Using fallback data: CRZ=%s, Ridership=%s, Entrances=%s",
                 len(crz_raw), len(ridership_raw), len(entrances_raw))

    # --- 2. Cleaning ---
    log.info("Step 2: Data cleaning")
    crz_clean = clean_crz(crz_raw)
    ridership_clean = clean_ridership(ridership_raw)
    entrances_clean = clean_station_entrances(entrances_raw)
    log.info("Cleaned: CRZ=%s, Ridership=%s, Entrances=%s", len(crz_clean), len(ridership_clean), len(entrances_clean))

    # --- 3. Synthetic expansion ---
    log.info("Step 3: Synthetic expansion to target row counts")
    crz_expanded = expand_crz_to_target(crz_clean, target_rows=target_crz_rows)
    ridership_expanded = expand_ridership_to_target(ridership_clean, target_rows=target_ridership_rows)
    log.info("Expanded: CRZ=%s, Ridership=%s", len(crz_expanded), len(ridership_expanded))

    # --- 4. Dimension lookups ---
    lookups = build_dimension_lookups(crz_clean, ridership_clean, entrances_clean)
    stats["tables"]["Dim_Date"] = len(lookups["dim_date"])
    stats["tables"]["Dim_Time"] = len(lookups["dim_time"])
    stats["tables"]["Dim_Vehicle_Class"] = len(lookups["dim_vehicle_class"])
    stats["tables"]["Dim_Location"] = len(lookups["dim_location"])
    stats["tables"]["Dim_Transport_Mode"] = len(lookups["dim_transport_mode"])
    stats["tables"]["Dim_Station"] = len(lookups["dim_station"])
    stats["tables"]["Dim_Entrance"] = len(lookups["dim_entrance"])

    # --- 5. Detect databases and insert ---
    pg_ok, mysql_ok = detect_databases()
    log.info("Databases available: PostgreSQL=%s, MySQL=%s", pg_ok, mysql_ok)
    if not pg_ok and not mysql_ok:
        log.error("No database connection available. Ensure PostgreSQL or MySQL is running.")
        stats["errors"].append(("database", "No connection"))
        stats["total_seconds"] = time.perf_counter() - start_total
        return stats

    insert_start = time.perf_counter()
    total_inserted = 0

    if pg_ok:
        try:
            conn = get_postgres_connection()
            log.info("Inserting dimensions (PostgreSQL)...")
            insert_dimensions_pg(conn, lookups)
            for name, count in stats["tables"].items():
                log.info("  %s: %s rows", name, count)
            log.info("Inserting Fact_CRZ_Entries (PostgreSQL)...")
            n_crz = insert_fact_crz_pg(conn, crz_expanded, lookups)
            log.info("  Fact_CRZ_Entries: %s rows", n_crz)
            log.info("Inserting Fact_Ridership (PostgreSQL)...")
            n_rid = insert_fact_ridership_pg(conn, ridership_expanded, lookups)
            log.info("  Fact_Ridership: %s rows", n_rid)
            run_analyze_pg(conn)
            conn.close()
            stats["tables"]["Fact_CRZ_Entries_pg"] = n_crz
            stats["tables"]["Fact_Ridership_pg"] = n_rid
            total_inserted += n_crz + n_rid
        except Exception as e:
            log.exception("PostgreSQL insert failed: %s", e)
            stats["errors"].append(("postgres", str(e)))

    if mysql_ok:
        try:
            conn = get_mysql_connection()
            log.info("Inserting dimensions (MySQL)...")
            insert_dimensions_mysql(conn, lookups)
            log.info("Inserting Fact_CRZ_Entries (MySQL)...")
            n_crz = insert_fact_crz_mysql(conn, crz_expanded, lookups)
            log.info("  Fact_CRZ_Entries: %s rows", n_crz)
            log.info("Inserting Fact_Ridership (MySQL)...")
            n_rid = insert_fact_ridership_mysql(conn, ridership_expanded, lookups)
            log.info("  Fact_Ridership: %s rows", n_rid)
            run_analyze_mysql(conn)
            conn.close()
            stats["tables"]["Fact_CRZ_Entries_mysql"] = n_crz
            stats["tables"]["Fact_Ridership_mysql"] = n_rid
            total_inserted += n_crz + n_rid
        except Exception as e:
            log.exception("MySQL insert failed: %s", e)
            stats["errors"].append(("mysql", str(e)))

    stats["total_rows_inserted"] = total_inserted
    stats["total_seconds"] = time.perf_counter() - start_total
    insert_seconds = time.perf_counter() - insert_start
    stats["insert_seconds"] = insert_seconds
    stats["rows_per_second"] = total_inserted / insert_seconds if insert_seconds > 0 else 0

    return stats


def main():
    """Entry point: run loader and print statistics."""
    log.info("NYC Traffic Congestion — Data loader started")
    stats = load_all(
        target_crz_rows=TARGET_CRZ_ROWS,
        target_ridership_rows=TARGET_RIDERSHIP_ROWS,
        chunk_size=50_000,
        use_download=True,
    )
    # --- Output statistics ---
    print("\n" + "=" * 60)
    print("LOAD STATISTICS")
    print("=" * 60)
    print("Rows inserted per table:")
    for table, count in sorted(stats["tables"].items(), key=lambda x: x[0]):
        print(f"  {table}: {count:,}")
    print(f"\nTotal load time: {stats['total_seconds']:.2f} seconds")
    print(f"Insert phase: {stats.get('insert_seconds', 0):.2f} seconds")
    print(f"Average insert speed: {stats.get('rows_per_second', 0):,.0f} rows/second")
    if stats.get("errors"):
        print("\nErrors encountered:")
        for kind, msg in stats["errors"]:
            print(f"  [{kind}] {msg}")
    print("=" * 60)
    log.info("Data loader finished")


if __name__ == "__main__":
    main()
