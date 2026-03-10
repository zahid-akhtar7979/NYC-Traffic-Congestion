"""
Synthetic data generator: expand cleaned datasets to target row counts.
Fact_CRZ_Entries ~1,000,000 rows; Fact_Ridership ~100,000 rows.
Uses randomized variations (vehicle_class_id, time_id, date_id, entry_count).
"""
import random
from typing import Any

import pandas as pd
import numpy as np

TARGET_CRZ_ROWS = 1_000_000
TARGET_RIDERSHIP_ROWS = 100_000


def _randomize_int(values: list[int] | pd.Series, size: int, rng: np.random.Generator) -> np.ndarray:
    """Draw size samples from values with replacement."""
    arr = np.asarray(values)
    if len(arr) == 0:
        return np.zeros(size, dtype=int)
    return rng.choice(arr, size=size, replace=True)


def expand_crz_to_target(
    df: pd.DataFrame,
    target_rows: int = TARGET_CRZ_ROWS,
    seed: int | None = 42,
) -> pd.DataFrame:
    """
    Replicate CRZ rows with randomized variations until target_rows is reached.
    Assumes df has columns: toll_date, hour_of_day, vehicle_class, detection_region, crz_entries.
    Returns dataframe with same columns; may add surrogate date_id/hour for DB use later.
    """
    rng = np.random.default_rng(seed)
    n = len(df)
    if n == 0:
        return df
    if n >= target_rows:
        return df.head(target_rows).reset_index(drop=True)

    # Build arrays for repeated rows with small variations
    repeats = (target_rows + n - 1) // n
    pieces = []
    for _ in range(repeats):
        chunk = df.copy()
        # Randomize hour within 0-23
        chunk["hour_of_day"] = rng.integers(0, 24, size=len(chunk))
        # Vary entry_count slightly (±20%, at least 1)
        scale = 0.8 + rng.random(size=len(chunk)) * 0.4
        chunk["crz_entries"] = np.maximum(1, (chunk["crz_entries"] * scale).astype(int))
        pieces.append(chunk)
    out = pd.concat(pieces, ignore_index=True)
    # Trim to exact target
    out = out.head(target_rows)
    return out


def expand_ridership_to_target(
    df: pd.DataFrame,
    target_rows: int = TARGET_RIDERSHIP_ROWS,
    seed: int | None = 42,
) -> pd.DataFrame:
    """
    Replicate ridership rows to target_rows with optional date jitter.
    Assumes df has columns: date, mode, count.
    """
    rng = np.random.default_rng(seed)
    n = len(df)
    if n == 0:
        return df
    if n >= target_rows:
        return df.head(target_rows).reset_index(drop=True)

    repeats = (target_rows + n - 1) // n
    pieces = []
    for _ in range(repeats):
        chunk = df.copy()
        # Slight count variation
        scale = 0.9 + rng.random(size=len(chunk)) * 0.2
        chunk["count"] = np.maximum(0, (chunk["count"] * scale).astype(int))
        pieces.append(chunk)
    out = pd.concat(pieces, ignore_index=True)
    return out.head(target_rows)
