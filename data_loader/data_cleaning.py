"""
Data cleaning and normalization for NYC Open Data datasets.
Maps dataset columns to database schema (Dim_* and Fact_* columns).
"""
from typing import Any

import pandas as pd

# --- Column name normalization (NYC Open Data may use different casings) ---

# CRZ: Toll Date, Hour of Day, Vehicle Class, Detection Region, CRZ Entries
CRZ_COL_MAP = {
    "toll date": "toll_date",
    "toll_date": "toll_date",
    "hour of day": "hour_of_day",
    "hour_of_day": "hour_of_day",
    "vehicle class": "vehicle_class",
    "vehicle_class": "vehicle_class",
    "detection region": "detection_region",
    "detection_region": "detection_region",
    "crz entries": "crz_entries",
    "crz_entries": "crz_entries",
}

# Ridership: Date, Mode, Count
RIDERSHIP_COL_MAP = {
    "date": "date",
    "mode": "mode",
    "transport_mode": "mode",
    "count": "count",
    "ridership_count": "count",
}

# Station/Entrance: Stop Name, Borough, Entrance Latitude, Entrance Longitude, Entrance Type
STATION_COL_MAP = {
    "stop name": "stop_name",
    "stop_name": "stop_name",
    "station name": "stop_name",
    "station_name": "stop_name",
    "borough": "borough",
    "entrance latitude": "entrance_latitude",
    "entrance_latitude": "entrance_latitude",
    "entrance longitude": "entrance_longitude",
    "entrance_longitude": "entrance_longitude",
    "entrance type": "entrance_type",
    "entrance_type": "entrance_type",
    "line": "line",
}


def _normalize_columns(df: pd.DataFrame, col_map: dict[str, str]) -> pd.DataFrame:
    """Rename columns to canonical names using case-insensitive match."""
    rename = {}
    for c in df.columns:
        key = str(c).strip().lower()
        if key in col_map:
            rename[c] = col_map[key]
    return df.rename(columns=rename) if rename else df


def _safe_int(val: Any, default: int = 0) -> int:
    """Coerce value to int; return default on failure."""
    if pd.isna(val):
        return default
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Coerce value to float; return default on failure."""
    if pd.isna(val):
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _parse_date(s: Any) -> str | None:
    """Parse date to YYYY-MM-DD string."""
    if pd.isna(s):
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        dt = pd.to_datetime(s)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def clean_crz(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize CRZ entries dataset.
    Output columns: toll_date, hour_of_day, vehicle_class, detection_region, crz_entries.
    """
    df = _normalize_columns(df.copy(), CRZ_COL_MAP)
    out = pd.DataFrame()
    out["toll_date"] = df.get("toll_date", pd.Series(dtype=object)).apply(_parse_date)
    out["hour_of_day"] = df.get("hour_of_day", pd.Series(dtype=object)).apply(lambda x: _safe_int(x, 0))
    out["vehicle_class"] = df.get("vehicle_class", pd.Series(dtype=object)).astype(str).str.strip()
    out["detection_region"] = df.get("detection_region", pd.Series(dtype=object)).astype(str).str.strip()
    out["crz_entries"] = df.get("crz_entries", pd.Series(dtype=object)).apply(lambda x: _safe_int(x, 0))
    # Drop rows missing required fields
    out = out.dropna(subset=["toll_date", "vehicle_class"])
    out = out[out["crz_entries"] >= 0]
    out["hour_of_day"] = out["hour_of_day"].clip(0, 23)
    return out.reset_index(drop=True)


def clean_ridership(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize daily ridership dataset.
    Output columns: date, mode, count.
    """
    df = _normalize_columns(df.copy(), RIDERSHIP_COL_MAP)
    out = pd.DataFrame()
    out["date"] = df.get("date", pd.Series(dtype=object)).apply(_parse_date)
    out["mode"] = df.get("mode", pd.Series(dtype=object)).astype(str).str.strip()
    out["count"] = df.get("count", pd.Series(dtype=object)).apply(lambda x: _safe_int(x, 0))
    out = out.dropna(subset=["date", "mode"])
    out = out[out["count"] >= 0]
    return out.reset_index(drop=True)


def clean_station_entrances(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean subway entrances dataset.
    Output columns: stop_name, borough, entrance_latitude, entrance_longitude, entrance_type, line.
    """
    df = _normalize_columns(df.copy(), STATION_COL_MAP)
    out = pd.DataFrame()
    out["stop_name"] = df.get("stop_name", pd.Series(dtype=object)).astype(str).str.strip()
    out["borough"] = df.get("borough", pd.Series(dtype=object)).astype(str).str.strip()
    out["entrance_latitude"] = df.get("entrance_latitude", pd.Series(dtype=object)).apply(_safe_float)
    out["entrance_longitude"] = df.get("entrance_longitude", pd.Series(dtype=object)).apply(_safe_float)
    out["entrance_type"] = df.get("entrance_type", pd.Series(dtype=object)).astype(str).str.strip()
    out["line"] = df.get("line", pd.Series(dtype=object)).astype(str).str.strip()
    out = out.dropna(subset=["stop_name"])
    return out.reset_index(drop=True)
