"""
Dataset ingestion module for NYC Open Data.
Downloads CSVs with retry logic and returns data via pandas (chunked for memory efficiency).
"""
import io
import os
import sys
import time

import pandas as pd
import requests

# Project root on path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

# NYC Open Data dataset URLs (CSV export)
URL_CRZ_ENTRIES = "https://data.ny.gov/resource/t6yz-b64h.csv"
URL_DAILY_RIDERSHIP = "https://data.ny.gov/resource/sayj-mze2.csv"
URL_SUBWAY_ENTRANCES = "https://data.ny.gov/resource/i9wp-a4ja.csv"

# Alternative download URL format (rows.csv) if resource endpoint is restricted
URL_CRZ_ALT = "https://data.ny.gov/api/views/t6yz-b64h/rows.csv?accessType=DOWNLOAD"
URL_RIDERSHIP_ALT = "https://data.ny.gov/api/views/sayj-mze2/rows.csv?accessType=DOWNLOAD"
URL_ENTRANCES_ALT = "https://data.ny.gov/api/views/i9wp-a4ja/rows.csv?accessType=DOWNLOAD"

DEFAULT_CHUNK_SIZE = 50_000
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 2
REQUEST_TIMEOUT = 120


def _download_with_retry(url: str, session: requests.Session | None = None) -> requests.Response:
    """Download URL with retries and backoff. Raises on final failure."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", "NYC-Traffic-Congestion-Loader/1.0")
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
    raise last_error


def _read_csv_from_response(response: requests.Response, chunk_size: int | None) -> pd.DataFrame | None:
    """Read CSV from response content; if chunk_size set, read in chunks and concatenate."""
    content = response.content
    buf = io.BytesIO(content)
    if chunk_size is None:
        return pd.read_csv(buf, low_memory=False)
    chunks = []
    for chunk in pd.read_csv(buf, chunksize=chunk_size, low_memory=False):
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True) if chunks else None


def fetch_crz_entries(chunk_size: int | None = DEFAULT_CHUNK_SIZE) -> pd.DataFrame:
    """
    Download Congestion Zone Vehicle Entries dataset.
    Returns a single DataFrame (chunked read for memory efficiency if chunk_size set).
    """
    for url in (URL_CRZ_ENTRIES, URL_CRZ_ALT):
        try:
            resp = _download_with_retry(url)
            df = _read_csv_from_response(resp, chunk_size)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    raise RuntimeError("Could not download CRZ entries from any URL")


def fetch_daily_ridership(chunk_size: int | None = DEFAULT_CHUNK_SIZE) -> pd.DataFrame:
    """Download Daily Ridership dataset."""
    for url in (URL_DAILY_RIDERSHIP, URL_RIDERSHIP_ALT):
        try:
            resp = _download_with_retry(url)
            df = _read_csv_from_response(resp, chunk_size)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    raise RuntimeError("Could not download daily ridership from any URL")


def fetch_subway_entrances(chunk_size: int | None = DEFAULT_CHUNK_SIZE) -> pd.DataFrame:
    """Download Subway Entrances and Exits dataset."""
    for url in (URL_SUBWAY_ENTRANCES, URL_ENTRANCES_ALT):
        try:
            resp = _download_with_retry(url)
            df = _read_csv_from_response(resp, chunk_size)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    raise RuntimeError("Could not download subway entrances from any URL")


def fetch_all_datasets(
    chunk_size: int | None = DEFAULT_CHUNK_SIZE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Download all three datasets. Returns (crz_df, ridership_df, entrances_df)."""
    crz = fetch_crz_entries(chunk_size=chunk_size)
    ridership = fetch_daily_ridership(chunk_size=chunk_size)
    entrances = fetch_subway_entrances(chunk_size=chunk_size)
    return crz, ridership, entrances
