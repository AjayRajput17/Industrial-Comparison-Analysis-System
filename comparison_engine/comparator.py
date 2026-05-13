"""
comparator.py — Core comparison engine using 9-column business identity key.

Compares OLD and NEW datasets using:
  MODEL YEAR + PART NO + VEH FAM + VEH LINE + DEPT_REL +
  PART USAGE DESC + PHYSCL DESC + ENGINE + TRANSMISSION

Classifies every row into: No Change, Modified, New, or Deleted.

IMPORTANT:
  - NO deduplication is performed (drop_duplicates removed).
  - All valid business rows are preserved.
  - Duplicate identity collisions are reported, not silently discarded.
"""

import pandas as pd
import numpy as np
from preprocessing.analysis import normalize_columns, resolve_column
from config.comparison_identity import IDENTITY_COLUMNS, IDENTITY_CANDIDATES


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


def _normalize_key_part(series):
    """Normalize a Series for key building: fillna, strip, upper, remove .0"""
    s = series.fillna("").astype(str).str.strip().str.upper()
    s = s.str.replace(r'\.0$', '', regex=True)
    return s


def build_business_identity_key(df):
    """
    Build a 9-column business identity key (__KEY__) from the DataFrame.

    Key = MODEL_YEAR|PART_NO|VEH_FAM|VEH_LINE|DEPT_REL|
          PART_USAGE_DESC|PHYSCL_DESC|ENGINE|TRANSMISSION

    Parameters
    ----------
    df : DataFrame with normalized (uppercase) column names.

    Returns
    -------
    (df_with_key, diagnostics)
        df_with_key: DataFrame with __KEY__ column added.
        diagnostics: dict with identity building metadata.
    """
    df = df.copy()
    cols = list(df.columns)
    diagnostics = {}

    resolved = {}
    missing = []
    key_parts = []

    for identity_field in IDENTITY_COLUMNS:
        candidates = IDENTITY_CANDIDATES.get(identity_field, [identity_field])
        col = resolve_column(cols, candidates)

        if col:
            resolved[identity_field] = col
            key_parts.append(_normalize_key_part(df[col]))
        else:
            missing.append(identity_field)
            key_parts.append(pd.Series(["_"] * len(df), index=df.index))

    diagnostics["resolved_identity_columns"] = resolved
    diagnostics["missing_identity_columns"] = missing

    # Build the composite key by joining all 9 parts with pipe separator
    df["__KEY__"] = key_parts[0]
    for part in key_parts[1:]:
        df["__KEY__"] = df["__KEY__"] + "|" + part

    df["__KEY__"] = df["__KEY__"].fillna("").astype(str)

    # Drop rows where ALL segments are null/empty
    df = df[~df["__KEY__"].apply(
        lambda k: all(seg in _NULL_ALIASES for seg in k.split("|"))
    )]

    diagnostics["total_rows_after_key_build"] = len(df)

    # Detect duplicate keys (for diagnostics only — NOT removing them)
    key_counts = df["__KEY__"].value_counts()
    duplicate_keys = key_counts[key_counts > 1]
    diagnostics["duplicate_identity_count"] = len(duplicate_keys)
    diagnostics["total_duplicate_rows"] = int(duplicate_keys.sum() - len(duplicate_keys)) if len(duplicate_keys) > 0 else 0

    if not duplicate_keys.empty:
        diagnostics["sample_duplicate_keys"] = duplicate_keys.head(5).index.tolist()

    return df, diagnostics


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
    Compare two DataFrames using 9-column business identity key.

    Parameters
    ----------
    old_df, new_df : DataFrame
        Raw DataFrames as loaded from Excel (not yet normalized).

    Returns
    -------
    (modified_df, new_only_df, deleted_df, nochange_df, comp_diagnostics)
        Each DataFrame is clean with original column names.
        modified_df includes a 'CHANGES' dict column.
        comp_diagnostics contains full pipeline trace.
    """
    comp_diagnostics = {}

    # ── Normalize both ─────────────────────────────────────────────────────────
    old_norm, _ = normalize_columns(old_df)
    new_norm, _ = normalize_columns(new_df)

    from preprocessing.type_normalizer import normalize_types
    old_norm = normalize_types(old_norm)
    new_norm = normalize_types(new_norm)

    comp_diagnostics["old_rows_normalized"] = len(old_norm)
    comp_diagnostics["new_rows_normalized"] = len(new_norm)

    # ── Fix date columns ───────────────────────────────────────────────────────
    for frame in (old_norm, new_norm):
        for col in frame.columns:
            if 'DATE' in col.upper():
                try:
                    frame[col] = pd.to_datetime(frame[col], errors='coerce').dt.strftime('%Y-%m-%d')
                    frame[col] = frame[col].fillna('')
                except Exception:
                    pass

    # ── Build 9-column business identity keys ──────────────────────────────────
    old_keyed, old_key_diags = build_business_identity_key(old_norm)
    new_keyed, new_key_diags = build_business_identity_key(new_norm)

    comp_diagnostics["old_identity"] = old_key_diags
    comp_diagnostics["new_identity"] = new_key_diags

    # ── NO deduplication — preserve ALL valid business rows ────────────────────
    # Handle duplicate keys by grouping: for common keys with multiple rows,
    # we match by position within the group (first-to-first, second-to-second).

    # ── Set math on unique key sets ────────────────────────────────────────────
    old_keys = set(old_keyed["__KEY__"])
    new_keys = set(new_keyed["__KEY__"])

    common_keys   = old_keys & new_keys
    new_only_keys = new_keys - old_keys
    deleted_keys  = old_keys - new_keys

    comp_diagnostics["common_key_count"] = len(common_keys)
    comp_diagnostics["new_only_key_count"] = len(new_only_keys)
    comp_diagnostics["deleted_key_count"] = len(deleted_keys)

    # ── Determine non-key columns to compare ──────────────────────────────────
    compare_cols = [c for c in new_keyed.columns
                    if c in old_keyed.columns
                    and c != "__KEY__"
                    and c.upper() not in _SKIP_COMPARE]

    # ── Classify common keys ──────────────────────────────────────────────────
    modified_rows = []
    nochange_rows = []

    # Group both DataFrames by __KEY__ to handle duplicate keys correctly
    old_grouped = old_keyed.groupby("__KEY__", sort=False)
    new_grouped = new_keyed.groupby("__KEY__", sort=False)

    for key in common_keys:
        old_group = old_grouped.get_group(key)
        new_group = new_grouped.get_group(key)

        # Match rows positionally within each group
        max_rows = max(len(old_group), len(new_group))

        for i in range(max_rows):
            if i < len(old_group) and i < len(new_group):
                # Both exist at this position — compare
                old_row = old_group.iloc[i]
                new_row = new_group.iloc[i]

                changes = detect_changes(old_row, new_row, compare_cols)
                row_data = new_row.to_dict()
                row_data.pop("__KEY__", None)

                if changes:
                    row_data["CHANGES"] = changes
                    modified_rows.append(row_data)
                else:
                    nochange_rows.append(row_data)

            elif i >= len(old_group):
                # Extra row in NEW — treat as new
                row_data = new_group.iloc[i].to_dict()
                row_data.pop("__KEY__", None)
                # Tag as new — will be added to new_only below
                modified_rows.append(row_data)  # stored temporarily
                # Actually these are truly new rows within a common key
                # We'll handle them properly below

            elif i >= len(new_group):
                # Extra row in OLD — treat as deleted
                pass  # handled via deleted logic below

    # For keys with mismatched group sizes, handle extra rows
    extra_new_rows = []
    extra_deleted_rows = []

    for key in common_keys:
        old_group = old_grouped.get_group(key)
        new_group = new_grouped.get_group(key)

        if len(new_group) > len(old_group):
            # Extra new rows
            for i in range(len(old_group), len(new_group)):
                row_data = new_group.iloc[i].to_dict()
                row_data.pop("__KEY__", None)
                extra_new_rows.append(row_data)

        if len(old_group) > len(new_group):
            # Extra deleted rows
            for i in range(len(new_group), len(old_group)):
                row_data = old_group.iloc[i].to_dict()
                row_data.pop("__KEY__", None)
                extra_deleted_rows.append(row_data)

    # Remove the temporarily added extra new rows from modified_rows
    # (they were appended in the main loop — remove them)
    # Recalculate modified_rows cleanly
    modified_rows_clean = []
    nochange_rows_clean = []

    for key in common_keys:
        old_group = old_grouped.get_group(key)
        new_group = new_grouped.get_group(key)
        min_rows = min(len(old_group), len(new_group))

        for i in range(min_rows):
            old_row = old_group.iloc[i]
            new_row = new_group.iloc[i]

            changes = detect_changes(old_row, new_row, compare_cols)
            row_data = new_row.to_dict()
            row_data.pop("__KEY__", None)

            if changes:
                row_data["CHANGES"] = changes
                modified_rows_clean.append(row_data)
            else:
                nochange_rows_clean.append(row_data)

    # ── Build output DataFrames ────────────────────────────────────────────────
    modified_df = pd.DataFrame(modified_rows_clean) if modified_rows_clean else pd.DataFrame()
    nochange_df = pd.DataFrame(nochange_rows_clean) if nochange_rows_clean else pd.DataFrame()

    # New-only: keys exclusively in NEW + extra rows from common keys
    new_only_base = new_keyed[new_keyed["__KEY__"].isin(new_only_keys)].drop(
                        columns=["__KEY__"]).reset_index(drop=True)
    if extra_new_rows:
        extra_new_df = pd.DataFrame(extra_new_rows)
        new_only_df = pd.concat([new_only_base, extra_new_df], ignore_index=True)
    else:
        new_only_df = new_only_base

    # Deleted: keys exclusively in OLD + extra rows from common keys
    deleted_base = old_keyed[old_keyed["__KEY__"].isin(deleted_keys)].drop(
                       columns=["__KEY__"]).reset_index(drop=True)
    if extra_deleted_rows:
        extra_del_df = pd.DataFrame(extra_deleted_rows)
        deleted_df = pd.concat([deleted_base, extra_del_df], ignore_index=True)
    else:
        deleted_df = deleted_base

    comp_diagnostics["modified_count"] = len(modified_df)
    comp_diagnostics["nochange_count"] = len(nochange_df)
    comp_diagnostics["new_count"] = len(new_only_df)
    comp_diagnostics["deleted_count"] = len(deleted_df)
    comp_diagnostics["extra_new_from_common"] = len(extra_new_rows)
    comp_diagnostics["extra_deleted_from_common"] = len(extra_deleted_rows)

    return modified_df, new_only_df, deleted_df, nochange_df, comp_diagnostics
