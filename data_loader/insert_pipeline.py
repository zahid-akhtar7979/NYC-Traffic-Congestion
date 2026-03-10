"""
Database insertion pipeline: load dimensions from cleaned/synthetic data,
then batch-insert fact tables. Supports PostgreSQL and MySQL; detects which is available.
Batch size 10,000; commit every 10,000 rows. Runs ANALYZE after load; VACUUM for PostgreSQL.
"""
import os
import sys
from datetime import datetime
from typing import Any

import pandas as pd
import numpy as np

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.db_connections import get_postgres_connection, get_mysql_connection

BATCH_SIZE = 10_000
DATE_ID_FORMAT = "%Y%m%d"  # e.g. 20240101


def _date_to_date_id(s: str) -> int:
    """Convert YYYY-MM-DD to integer date_id."""
    if not s or (isinstance(s, float) and np.isnan(s)):
        return 20240101
    s = str(s).strip()[:10]
    return int(s.replace("-", "")) if len(s) == 10 else 20240101


def _hour_to_time_id(hour: int) -> int:
    """Map hour 0-23 to time_id (use hour as id for simplicity)."""
    return max(0, min(23, int(hour)))


def detect_databases() -> tuple[bool, bool]:
    """Try connecting to PostgreSQL and MySQL; return (pg_ok, mysql_ok)."""
    pg_ok, mysql_ok = False, False
    try:
        conn = get_postgres_connection()
        conn.close()
        pg_ok = True
    except Exception:
        pass
    try:
        conn = get_mysql_connection()
        conn.close()
        mysql_ok = True
    except Exception:
        pass
    return pg_ok, mysql_ok


def build_dimension_lookups(
    crz_clean: pd.DataFrame,
    ridership_clean: pd.DataFrame,
    entrances_clean: pd.DataFrame,
) -> dict[str, Any]:
    """
    Build unique dimension keys and return lookup dicts and dimension DataFrames
    for Dim_Date, Dim_Time, Dim_Vehicle_Class, Dim_Location (borough), Dim_Transport_Mode,
    Dim_Station, Dim_Entrance.
    """
    # Dim_Date: from crz + ridership dates
    dates = set()
    for _, row in crz_clean.iterrows():
        d = row.get("toll_date")
        if d:
            dates.add(_date_to_date_id(d))
    for _, row in ridership_clean.iterrows():
        d = row.get("date")
        if d:
            dates.add(_date_to_date_id(d))
    if not dates:
        dates = {20240101}
    date_list = sorted(dates)
    dim_date = []
    for date_id in date_list:
        s = str(date_id)
        y, m, d = int(s[:4]), int(s[4:6]), int(s[6:8])
        dt = datetime(y, m, d)
        dow = dt.strftime("%A")
        dim_date.append((date_id, f"{y}-{m:02d}-{d:02d}", y, m, d, dow))
    dim_date_df = pd.DataFrame(dim_date, columns=["date_id", "full_date", "year", "month", "day", "day_of_week"])

    # Dim_Time: hours 0-23
    dim_time = [(h, h, 0, "Hour" + str(h)) for h in range(24)]
    dim_time_df = pd.DataFrame(dim_time, columns=["time_id", "hour", "minute", "time_period"])

    # Dim_Vehicle_Class: from crz vehicle_class
    vc = crz_clean["vehicle_class"].dropna().astype(str).str.strip().unique()
    vc = [x for x in vc if x and x.lower() != "nan"]
    if not vc:
        vc = ["Passenger", "Truck", "Motorcycle"]
    dim_vc = [(i + 1, name) for i, name in enumerate(sorted(set(vc)))]
    dim_vc_df = pd.DataFrame(dim_vc, columns=["vehicle_class_id", "vehicle_class_name"])
    vc_name_to_id = {row["vehicle_class_name"]: row["vehicle_class_id"] for _, row in dim_vc_df.iterrows()}

    # Dim_Location: borough from crz detection_region
    boroughs = crz_clean["detection_region"].dropna().astype(str).str.strip().unique()
    boroughs = [x for x in boroughs if x and x.lower() != "nan"]
    if not boroughs:
        boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    dim_loc = [(i + 1, b, "", "", None, None) for i, b in enumerate(sorted(set(boroughs)))]
    dim_loc_df = pd.DataFrame(dim_loc, columns=["location_id", "borough", "street_name", "intersection", "latitude", "longitude"])
    borough_to_location_id = {row["borough"]: row["location_id"] for _, row in dim_loc_df.iterrows()}

    # Dim_Transport_Mode: from ridership mode
    modes = ridership_clean["mode"].dropna().astype(str).str.strip().unique()
    modes = [x for x in modes if x and x.lower() != "nan"]
    if not modes:
        modes = ["Subway", "Bus", "LIRR", "Metro-North"]
    dim_tm = [(i + 1, name) for i, name in enumerate(sorted(set(modes)))]
    dim_tm_df = pd.DataFrame(dim_tm, columns=["transport_mode_id", "transport_mode_name"])
    mode_name_to_id = {row["transport_mode_name"]: row["transport_mode_id"] for _, row in dim_tm_df.iterrows()}

    # Dim_Station: from entrances stop_name + borough
    station_keys = entrances_clean.groupby(["stop_name", "borough"]).size().reset_index()[["stop_name", "borough"]]
    station_keys = station_keys.drop_duplicates()
    dim_station = [(i + 1, row["stop_name"], row["borough"], "") for i, (_, row) in enumerate(station_keys.iterrows())]
    dim_station_df = pd.DataFrame(dim_station, columns=["station_id", "station_name", "borough", "line"])
    station_to_id = {}
    for _, row in dim_station_df.iterrows():
        key = (row["station_name"], row["borough"])
        station_to_id[key] = row["station_id"]

    # Dim_Entrance: one per entrance row, with station_id
    entrances_clean = entrances_clean.copy()
    entrances_clean["_station_key"] = list(zip(entrances_clean["stop_name"], entrances_clean["borough"]))
    entrances_clean["station_id"] = entrances_clean["_station_key"].map(station_to_id)
    entrances_clean = entrances_clean.dropna(subset=["station_id"])
    entrances_clean["station_id"] = entrances_clean["station_id"].astype(int)
    dim_entrance = []
    for idx, (_, row) in enumerate(entrances_clean.iterrows()):
        dim_entrance.append((
            idx + 1,
            int(row["station_id"]),
            str(row.get("entrance_type", ""))[:50],
            True,
            True,
            float(row.get("entrance_latitude", 0) or 0),
            float(row.get("entrance_longitude", 0) or 0),
        ))
    dim_entrance_df = pd.DataFrame(dim_entrance, columns=[
        "entrance_id", "station_id", "entrance_type", "entry_allowed", "exit_allowed", "latitude", "longitude"
    ])

    return {
        "dim_date": dim_date_df,
        "dim_time": dim_time_df,
        "dim_vehicle_class": dim_vc_df,
        "dim_location": dim_loc_df,
        "dim_transport_mode": dim_tm_df,
        "dim_station": dim_station_df,
        "dim_entrance": dim_entrance_df,
        "vc_name_to_id": vc_name_to_id,
        "borough_to_location_id": borough_to_location_id,
        "mode_name_to_id": mode_name_to_id,
        "date_list": date_list,
    }


def insert_dimensions_pg(conn, lookups: dict[str, Any]) -> None:
    """Insert all dimension tables (PostgreSQL)."""
    cur = conn.cursor()
    # Dim_Date
    for _, row in lookups["dim_date"].iterrows():
        cur.execute(
            "INSERT INTO Dim_Date (date_id, full_date, year, month, day, day_of_week) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (date_id) DO NOTHING",
            (row["date_id"], row["full_date"], row["year"], row["month"], row["day"], row["day_of_week"]),
        )
    for _, row in lookups["dim_time"].iterrows():
        cur.execute(
            "INSERT INTO Dim_Time (time_id, hour, minute, time_period) VALUES (%s, %s, %s, %s) ON CONFLICT (time_id) DO NOTHING",
            (row["time_id"], row["hour"], row["minute"], row["time_period"]),
        )
    for _, row in lookups["dim_vehicle_class"].iterrows():
        cur.execute(
            "INSERT INTO Dim_Vehicle_Class (vehicle_class_id, vehicle_class_name) VALUES (%s, %s) ON CONFLICT (vehicle_class_id) DO NOTHING",
            (row["vehicle_class_id"], row["vehicle_class_name"]),
        )
    for _, row in lookups["dim_location"].iterrows():
        cur.execute(
            "INSERT INTO Dim_Location (location_id, borough, street_name, intersection, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (location_id) DO NOTHING",
            (row["location_id"], row["borough"], row["street_name"], row["intersection"], row["latitude"], row["longitude"]),
        )
    for _, row in lookups["dim_transport_mode"].iterrows():
        cur.execute(
            "INSERT INTO Dim_Transport_Mode (transport_mode_id, transport_mode_name) VALUES (%s, %s) ON CONFLICT (transport_mode_id) DO NOTHING",
            (row["transport_mode_id"], row["transport_mode_name"]),
        )
    for _, row in lookups["dim_station"].iterrows():
        cur.execute(
            "INSERT INTO Dim_Station (station_id, station_name, borough, line) VALUES (%s, %s, %s, %s) ON CONFLICT (station_id) DO NOTHING",
            (row["station_id"], row["station_name"], row["borough"], row["line"]),
        )
    for _, row in lookups["dim_entrance"].iterrows():
        cur.execute(
            "INSERT INTO Dim_Entrance (entrance_id, station_id, entrance_type, entry_allowed, exit_allowed, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (entrance_id) DO NOTHING",
            (row["entrance_id"], row["station_id"], row["entrance_type"], row["entry_allowed"], row["exit_allowed"], row["latitude"], row["longitude"]),
        )
    conn.commit()
    cur.close()


def insert_dimensions_mysql(conn, lookups: dict[str, Any]) -> None:
    """Insert all dimension tables (MySQL)."""
    cur = conn.cursor()
    for _, row in lookups["dim_date"].iterrows():
        cur.execute(
            "INSERT IGNORE INTO Dim_Date (date_id, full_date, year, month, day, day_of_week) VALUES (%s, %s, %s, %s, %s, %s)",
            (row["date_id"], row["full_date"], row["year"], row["month"], row["day"], row["day_of_week"]),
        )
    for _, row in lookups["dim_time"].iterrows():
        cur.execute(
            "INSERT IGNORE INTO Dim_Time (time_id, hour, minute, time_period) VALUES (%s, %s, %s, %s)",
            (row["time_id"], row["hour"], row["minute"], row["time_period"]),
        )
    for _, row in lookups["dim_vehicle_class"].iterrows():
        cur.execute(
            "INSERT IGNORE INTO Dim_Vehicle_Class (vehicle_class_id, vehicle_class_name) VALUES (%s, %s)",
            (row["vehicle_class_id"], row["vehicle_class_name"]),
        )
    for _, row in lookups["dim_location"].iterrows():
        cur.execute(
            "INSERT IGNORE INTO Dim_Location (location_id, borough, street_name, intersection, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s)",
            (row["location_id"], row["borough"], row["street_name"], row["intersection"], row["latitude"], row["longitude"]),
        )
    for _, row in lookups["dim_transport_mode"].iterrows():
        cur.execute(
            "INSERT IGNORE INTO Dim_Transport_Mode (transport_mode_id, transport_mode_name) VALUES (%s, %s)",
            (row["transport_mode_id"], row["transport_mode_name"]),
        )
    for _, row in lookups["dim_station"].iterrows():
        cur.execute(
            "INSERT IGNORE INTO Dim_Station (station_id, station_name, borough, line) VALUES (%s, %s, %s, %s)",
            (row["station_id"], row["station_name"], row["borough"], row["line"]),
        )
    for _, row in lookups["dim_entrance"].iterrows():
        cur.execute(
            "INSERT IGNORE INTO Dim_Entrance (entrance_id, station_id, entrance_type, entry_allowed, exit_allowed, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (row["entrance_id"], row["station_id"], row["entrance_type"], row["entry_allowed"], row["exit_allowed"], row["latitude"], row["longitude"]),
        )
    conn.commit()
    cur.close()


def insert_fact_crz_pg(conn, crz_df: pd.DataFrame, lookups: dict[str, Any], batch_size: int = BATCH_SIZE) -> int:
    """Batch insert Fact_CRZ_Entries (PostgreSQL). crz_df has toll_date, hour_of_day, vehicle_class, detection_region, crz_entries."""
    vc = lookups["vc_name_to_id"]
    loc = lookups["borough_to_location_id"]
    cur = conn.cursor()
    rows = []
    for i, row in crz_df.iterrows():
        date_id = _date_to_date_id(row.get("toll_date", ""))
        time_id = _hour_to_time_id(row.get("hour_of_day", 0))
        vc_name = str(row.get("vehicle_class", "")).strip()
        vehicle_class_id = vc.get(vc_name, 1)
        borough = str(row.get("detection_region", "")).strip()
        location_id = loc.get(borough, 1)
        entry_count = int(row.get("crz_entries", 0))
        crz_entry_id = i + 1
        rows.append((crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count))
    inserted = 0
    q = "INSERT INTO Fact_CRZ_Entries (crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (crz_entry_id) DO NOTHING"
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cur.executemany(q, batch)
        inserted += len(batch)
        conn.commit()
    cur.close()
    return inserted


def insert_fact_crz_mysql(conn, crz_df: pd.DataFrame, lookups: dict[str, Any], batch_size: int = BATCH_SIZE) -> int:
    """Batch insert Fact_CRZ_Entries (MySQL)."""
    vc = lookups["vc_name_to_id"]
    loc = lookups["borough_to_location_id"]
    cur = conn.cursor()
    rows = []
    for i, row in crz_df.iterrows():
        date_id = _date_to_date_id(row.get("toll_date", ""))
        time_id = _hour_to_time_id(row.get("hour_of_day", 0))
        vc_name = str(row.get("vehicle_class", "")).strip()
        vehicle_class_id = vc.get(vc_name, 1)
        borough = str(row.get("detection_region", "")).strip()
        location_id = loc.get(borough, 1)
        entry_count = int(row.get("crz_entries", 0))
        crz_entry_id = i + 1
        rows.append((crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count))
    q = "INSERT IGNORE INTO Fact_CRZ_Entries (crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count) VALUES (%s, %s, %s, %s, %s, %s)"
    inserted = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cur.executemany(q, batch)
        inserted += len(batch)
        conn.commit()
    cur.close()
    return inserted


def insert_fact_ridership_pg(conn, ridership_df: pd.DataFrame, lookups: dict[str, Any], batch_size: int = BATCH_SIZE) -> int:
    """Batch insert Fact_Ridership (PostgreSQL)."""
    mode_to_id = lookups["mode_name_to_id"]
    cur = conn.cursor()
    rows = []
    for i, row in ridership_df.iterrows():
        date_id = _date_to_date_id(row.get("date", ""))
        mode_name = str(row.get("mode", "")).strip()
        transport_mode_id = mode_to_id.get(mode_name, 1)
        ridership_count = int(row.get("count", 0))
        ridership_fact_id = i + 1
        rows.append((ridership_fact_id, date_id, transport_mode_id, ridership_count))
    q = "INSERT INTO Fact_Ridership (ridership_fact_id, date_id, transport_mode_id, ridership_count) VALUES (%s, %s, %s, %s) ON CONFLICT (ridership_fact_id) DO NOTHING"
    inserted = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cur.executemany(q, batch)
        inserted += len(batch)
        conn.commit()
    cur.close()
    return inserted


def insert_fact_ridership_mysql(conn, ridership_df: pd.DataFrame, lookups: dict[str, Any], batch_size: int = BATCH_SIZE) -> int:
    """Batch insert Fact_Ridership (MySQL)."""
    mode_to_id = lookups["mode_name_to_id"]
    cur = conn.cursor()
    rows = []
    for i, row in ridership_df.iterrows():
        date_id = _date_to_date_id(row.get("date", ""))
        mode_name = str(row.get("mode", "")).strip()
        transport_mode_id = mode_to_id.get(mode_name, 1)
        ridership_count = int(row.get("count", 0))
        ridership_fact_id = i + 1
        rows.append((ridership_fact_id, date_id, transport_mode_id, ridership_count))
    q = "INSERT IGNORE INTO Fact_Ridership (ridership_fact_id, date_id, transport_mode_id, ridership_count) VALUES (%s, %s, %s, %s)"
    inserted = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cur.executemany(q, batch)
        inserted += len(batch)
        conn.commit()
    cur.close()
    return inserted


def run_analyze_pg(conn) -> None:
    """Run ANALYZE and VACUUM on PostgreSQL."""
    cur = conn.cursor()
    cur.execute("ANALYZE;")
    try:
        cur.execute("VACUUM ANALYZE Fact_CRZ_Entries;")
        cur.execute("VACUUM ANALYZE Fact_Ridership;")
    except Exception:
        pass
    conn.commit()
    cur.close()


def run_analyze_mysql(conn) -> None:
    """Run ANALYZE TABLE on MySQL. Consume all results to avoid 'Unread result found'."""
    cur = conn.cursor()
    for t in ["Fact_CRZ_Entries", "Fact_Ridership", "Dim_Date", "Dim_Time", "Dim_Vehicle_Class", "Dim_Location", "Dim_Transport_Mode", "Dim_Station", "Dim_Entrance"]:
        try:
            cur.execute(f"ANALYZE TABLE {t};")
            cur.fetchall()  # consume result so commit can proceed
        except Exception:
            pass
    conn.commit()
    cur.close()
