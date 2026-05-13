"""
Row ID Generator — Vectorized implementation.
Generates deterministic Row IDs using pandas vectorized string operations.
No row-by-row loops or .apply() calls.
"""

import pandas as pd
from config.rowid_config import ROW_ID_COLUMNS


def apply_row_ids(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    """
    Generate ROW IDs for the entire DataFrame using vectorized operations.
    Each ROW ID is a pipe-separated string of the configured columns.
    """
    if df.empty:
        df["ROW ID"] = []
        return df

    if columns is None:
        columns = ROW_ID_COLUMNS

    # Build list of normalized Series for each column
    parts = []
    for col in columns:
        if col in df.columns:
            s = df[col].fillna("").astype(str).str.strip()
            # Remove trailing .0 from floats (e.g. 2025.0 -> 2025)
            s = s.str.replace(r'\.0$', '', regex=True)
            parts.append(s)
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))

    # Vectorized concat using str.cat — orders of magnitude faster than .apply()
    df["ROW ID"] = parts[0].str.cat(parts[1:], sep="|")

    return df
