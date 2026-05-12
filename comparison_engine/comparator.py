"""
comparator.py — Core comparison engine using composite keys.

Compares OLD and NEW datasets using the composite key
(MODEL YEAR + PART NO + VEH FAM) and classifies every row into
one of: No Change, Modified, New, or Deleted.
"""

import pandas as pd
import numpy as np
from preprocessing.analysis import normalize_columns, resolve_column


# ── Column candidates (same as analysis.py) ───────────────────────────────────
_KEY_CANDIDATES = {
    "MODEL YEAR": ["MODEL YEAR", "MODEL_YEAR", "MODELYEAR", "MY"],
    "PART NO":    ["PART NO", "PART_NO", "PARTNO", "PART NUMBER", "PART_NUMBER"],
    "VEH FAM":   ["VEH FAM", "VEH_FAM", "VEHFAM", "VEHICLE FAMILY",
                   "VEHICLE_FAMILY"],
}

_NULL_ALIASES = frozenset({"", "NAN", "NONE", "NAT", "<NA>", "NULL", "_"})

# Columns to NEVER compare (unique per row, irrelevant to part data)
_SKIP_COMPARE = frozenset({
    "ROW ID", "ROW_ID", "ROWID", "ROW NO", "ROW_NO",
    "SR NO", "SR_NO", "SERIAL NO", "SERIAL_NO", "S NO", "S.NO",
    "INDEX", "__KEY__",
    "COMMENT", "COMMENTS",
})


def _safe_str(val):
    """Convert a value to a comparable string, treating NaN as empty."""
    if val is None:
        return ""
    if isinstance(val, float) and np.isnan(val):
        return ""
    return str(val).strip()


def build_composite_key(df):
    """
    Add a `__KEY__` column to the DataFrame.

    Key = MODEL_YEAR|PART_NO|VEH_FAM
    Falls back to MODEL_YEAR|PART_NO if VEH FAM is missing.

    Parameters
    ----------
    df : DataFrame
        Must have normalized (uppercase) column names.

    Returns
    -------
    DataFrame with __KEY__ column added.
    """
    df = df.copy()
    cols = list(df.columns)

    my_col  = resolve_column(cols, _KEY_CANDIDATES["MODEL YEAR"])
    pn_col  = resolve_column(cols, _KEY_CANDIDATES["PART NO"])
    vf_col  = resolve_column(cols, _KEY_CANDIDATES["VEH FAM"])

    if not pn_col:
        raise ValueError("PART NO column not found — cannot build composite key.")

    parts = []

    if my_col:
        s_my = df[my_col].fillna("").astype(str).str.strip().str.upper()
        s_my = s_my.str.replace(r'\.0$', '', regex=True)
        parts.append(s_my)
    else:
        parts.append(pd.Series(["_"] * len(df), index=df.index))

    s_pn = df[pn_col].fillna("").astype(str).str.strip().str.upper()
    s_pn = s_pn.str.replace(r'\.0$', '', regex=True)
    parts.append(s_pn)

    if vf_col:
        s_vf = df[vf_col].fillna("").astype(str).str.strip().str.upper()
        s_vf = s_vf.str.replace(r'\.0$', '', regex=True)
        parts.append(s_vf)
    else:
        parts.append(pd.Series(["_"] * len(df), index=df.index))

    df["__KEY__"] = parts[0] + "|" + parts[1] + "|" + parts[2]
    df["__KEY__"] = df["__KEY__"].fillna("").astype(str)

    # Drop rows with effectively null keys
    df = df[~df["__KEY__"].apply(
        lambda k: all(seg in _NULL_ALIASES for seg in k.split("|"))
    )]

    return df


def detect_changes(old_row, new_row, compare_cols):
    """
    Column-by-column comparison of two rows.

    Returns
    -------
    dict : {column: "old_value → new_value"} for columns that differ.
           Empty dict {} if all values match.
    """
    changes = {}
    for col in compare_cols:
        old_val = _safe_str(old_row.get(col, ""))
        new_val = _safe_str(new_row.get(col, ""))
        
        is_diff = old_val != new_val
        
        # Check if they are numerically equivalent (e.g., "0.0" and "0")
        if is_diff:
            try:
                if float(old_val) == float(new_val):
                    is_diff = False
            except ValueError:
                pass
                
        if is_diff:
            changes[col] = f"{old_val} → {new_val}"
    return changes


def compare_datasets(old_df, new_df):
    """
    Compare two DataFrames using composite key matching.

    Parameters
    ----------
    old_df, new_df : DataFrame
        Raw DataFrames as loaded from Excel (not yet normalized).

    Returns
    -------
    (modified_df, new_only_df, deleted_df, nochange_df)
        Each is a clean DataFrame with original column names + COMMENTS-ready data.
        modified_df includes a 'CHANGES' dict column (to be processed later).
    """
    # ── Normalize both ─────────────────────────────────────────────────────────
    old_norm, _ = normalize_columns(old_df)
    new_norm, _ = normalize_columns(new_df)

    # ── Fix date columns (Excel serial numbers → readable date strings) ────────
    for frame in (old_norm, new_norm):
        for col in frame.columns:
            if 'DATE' in col.upper():
                try:
                    frame[col] = pd.to_datetime(frame[col], errors='coerce').dt.strftime('%Y-%m-%d')
                    frame[col] = frame[col].fillna('')
                except Exception:
                    pass

    # ── Build keys ─────────────────────────────────────────────────────────────
    old_keyed = build_composite_key(old_norm)
    new_keyed = build_composite_key(new_norm)

    # ── Deduplicate on key (keep first occurrence) ─────────────────────────────
    old_keyed = old_keyed.drop_duplicates(subset=["__KEY__"], keep="first")
    new_keyed = new_keyed.drop_duplicates(subset=["__KEY__"], keep="first")

    # ── Set math ───────────────────────────────────────────────────────────────
    old_keys = set(old_keyed["__KEY__"])
    new_keys = set(new_keyed["__KEY__"])

    common_keys  = old_keys & new_keys
    new_only_keys = new_keys - old_keys
    deleted_keys  = old_keys - new_keys

    # ── Determine non-key columns to compare ──────────────────────────────────
    # Exclude __KEY__ and skip columns (ROW ID etc.)
    compare_cols = [c for c in new_keyed.columns
                    if c in old_keyed.columns
                    and c != "__KEY__"
                    and c.upper() not in _SKIP_COMPARE]

    # ── Classify common keys into Modified vs No Change ────────────────────────
    modified_rows = []
    nochange_rows = []

    # Build lookup dicts for O(1) access
    old_lookup = old_keyed.set_index("__KEY__")
    new_lookup = new_keyed.set_index("__KEY__")

    for key in common_keys:
        old_row = old_lookup.loc[key]
        new_row = new_lookup.loc[key]

        changes = detect_changes(old_row, new_row, compare_cols)

        row_data = new_row.to_dict()
        row_data.pop("__KEY__", None)

        if changes:
            row_data["CHANGES"] = changes
            modified_rows.append(row_data)
        else:
            nochange_rows.append(row_data)

    # ── Build output DataFrames ────────────────────────────────────────────────
    modified_df  = pd.DataFrame(modified_rows)  if modified_rows  else pd.DataFrame()
    nochange_df  = pd.DataFrame(nochange_rows)  if nochange_rows  else pd.DataFrame()
    new_only_df  = new_keyed[new_keyed["__KEY__"].isin(new_only_keys)].drop(
                       columns=["__KEY__"]).reset_index(drop=True)
    deleted_df   = old_keyed[old_keyed["__KEY__"].isin(deleted_keys)].drop(
                       columns=["__KEY__"]).reset_index(drop=True)

    return modified_df, new_only_df, deleted_df, nochange_df
