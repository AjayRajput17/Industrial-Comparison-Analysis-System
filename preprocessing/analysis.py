"""
analysis.py — File structure analysis & column normalization.

Dynamically detects column names, normalizes them, and resolves
required key columns (MODEL YEAR, PART NO, VEH FAM) regardless
of naming variations in the input files.
"""

import pandas as pd
import re

def clean_hidden_characters(val: str) -> str:
    """Removes invisible unicode characters and zero-width spaces."""
    if not isinstance(val, str):
        val = str(val)
    # Remove control characters and non-printable unicode
    val = re.sub(r'[\x00-\x1F\x7F-\x9F\u200B-\u200D\uFEFF]', '', val)
    return val

# ── Column resolution candidates ──────────────────────────────────────────────
_COLUMN_CANDIDATES = {
    "MODEL YEAR": ["MODEL YEAR", "MODEL_YEAR", "MODELYEAR", "MY"],
    "PART NO":    ["PART NO", "PART_NO", "PARTNO", "PART NUMBER", "PART_NUMBER"],
    "VEH FAM":   ["VEH FAM", "VEH_FAM", "VEHFAM", "VEHICLE FAMILY",
                   "VEHICLE_FAMILY"],
}


def resolve_column(columns, candidates):
    """
    Flexibly resolve a column name from a list of candidates.

    Parameters
    ----------
    columns : list[str]
        Actual column names (already normalized to uppercase + stripped).
    candidates : list[str]
        Possible name variations to look for (uppercase).

    Returns
    -------
    str or None
        The actual column name found, or None.
    """
    col_set = {c.strip().upper() for c in columns}

    # 1. Exact match
    for c in candidates:
        if c in col_set:
            # Return the original-cased version
            for orig in columns:
                if orig.strip().upper() == c:
                    return orig
            return c

    # 2. Partial / substring match (e.g. column contains "PART NO" somewhere)
    for c in candidates:
        for orig in columns:
            if c in orig.strip().upper():
                return orig

    return None


def normalize_columns(df):
    """
    Normalize all column names: uppercase + strip whitespace,
    and remove any unexpected file-specific prefixes like 'yyyy-mm-dd.COLUMN_NAME'.

    Returns
    -------
    (cleaned_df, column_map)
        cleaned_df : DataFrame with normalized column names
        column_map : dict mapping original_name → normalized_name
    """
    column_map = {}
    new_cols = []
    for col in df.columns:
        normalized = clean_hidden_characters(str(col)).strip().upper()
        # Remove duplicate spaces
        normalized = " ".join(normalized.split())
        # Remove prefix if there is a dot like 'PREFIX.COLUMN'
        if '.' in normalized:
            normalized = normalized.split('.')[-1].strip()

        column_map[col] = normalized
        new_cols.append(normalized)

    cleaned_df = df.copy()
    cleaned_df.columns = new_cols

    return cleaned_df, column_map

def analyze_file_structure(df):
    """
    Analyze an input DataFrame and return a structured summary.

    Returns
    -------
    dict with keys:
        column_names  : list of original column names
        dtypes        : dict of column → dtype string
        row_count     : int
        sample_rows   : first 5 rows as list of dicts
        key_columns   : dict {"MODEL YEAR": resolved, "PART NO": resolved, ...}
        column_map    : original → normalized mapping
        missing_keys  : list of required keys that could NOT be resolved
    """
    cleaned_df, column_map = normalize_columns(df)
    norm_cols = list(cleaned_df.columns)

    # Resolve key columns
    key_columns = {}
    missing_keys = []
    for logical_name, candidates in _COLUMN_CANDIDATES.items():
        resolved = resolve_column(norm_cols, candidates)
        if resolved:
            key_columns[logical_name] = resolved
        else:
            missing_keys.append(logical_name)

    return {
        "column_names": list(df.columns),
        "dtypes":       {str(c): str(d) for c, d in df.dtypes.items()},
        "row_count":    len(df),
        "sample_rows":  df.head(5).to_dict(orient="records"),
        "key_columns":  key_columns,
        "column_map":   column_map,
        "missing_keys": missing_keys,
    }
