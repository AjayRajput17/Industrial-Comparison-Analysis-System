"""
comparator.py — Core comparison engine using 9-column business identity key.

Compares OLD and NEW datasets using:
  MODEL YEAR + PART NO + VEH FAM + VEH LINE + DEPT_REL +
  PART USAGE DESC + PHYSCL DESC + ENGINE + TRANSMISSION

Classifies every row into: No Change, Modified, New, or Deleted.

PERFORMANCE OPTIMIZATIONS:
  - Single groupby per dataset, cached as dict of list-of-dicts
  - Single pass over common keys (no repeated groupby lookups)
  - Pre-converted rows to dicts for O(1) field access
  - DEBUG_MODE flag to skip expensive diagnostics in production
"""

import pandas as pd
import numpy as np
from preprocessing.analysis import normalize_columns, resolve_column
from config.comparison_identity import IDENTITY_COLUMNS, IDENTITY_CANDIDATES
from config.debug_config import DEBUG_MODE


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


def build_business_identity_key(df, collect_debug=False):
    """
    Build a 9-column business identity key (__KEY__) from the DataFrame.

    Parameters
    ----------
    df : DataFrame with normalized (uppercase) column names.
    collect_debug : bool, if True collect expensive diagnostics.

    Returns
    -------
    (df_with_key, diagnostics)
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

    # Build key using vectorized concat (faster than repeated + operator)
    df["__KEY__"] = key_parts[0].str.cat(key_parts[1:], sep="|")
    df["__KEY__"] = df["__KEY__"].fillna("").astype(str)

    # Drop rows where ALL segments are null/empty
    df = df[~df["__KEY__"].apply(
        lambda k: all(seg in _NULL_ALIASES for seg in k.split("|"))
    )]

    diagnostics["total_rows_after_key_build"] = len(df)

    # Duplicate diagnostics — only compute expensive parts in debug mode
    if collect_debug:
        key_counts = df["__KEY__"].value_counts()
        duplicate_keys = key_counts[key_counts > 1]
        diagnostics["duplicate_identity_count"] = len(duplicate_keys)
        diagnostics["total_duplicate_rows"] = int(duplicate_keys.sum() - len(duplicate_keys)) if len(duplicate_keys) > 0 else 0
        if not duplicate_keys.empty:
            diagnostics["sample_duplicate_keys"] = duplicate_keys.head(5).index.tolist()
    else:
        # Lightweight: just count duplicated keys
        dup_mask = df["__KEY__"].duplicated(keep=False)
        diagnostics["duplicate_identity_count"] = df.loc[dup_mask, "__KEY__"].nunique()
        diagnostics["total_duplicate_rows"] = int(dup_mask.sum()) - diagnostics["duplicate_identity_count"]

    return df, diagnostics


def _detect_changes_dict(old_dict, new_dict, compare_cols):
    """
    Compare two row dicts. Returns changes dict.
    Optimized: operates on pre-built dicts, not pandas Series.
    """
    changes = {}
    for col in compare_cols:
        old_val = _safe_str(old_dict.get(col, ""))
        new_val = _safe_str(new_dict.get(col, ""))

        if old_val != new_val:
            # Numeric equivalence check
            try:
                if float(old_val) == float(new_val):
                    continue
            except (ValueError, TypeError):
                pass
            changes[col] = f"{old_val} → {new_val}"
    return changes


def _build_group_dict(df_keyed):
    """
    Convert a keyed DataFrame into a dict of {key: [list of row dicts]}.
    This is done ONCE and reused everywhere — O(1) lookups thereafter.
    """
    groups = {}
    key_col_idx = df_keyed.columns.get_loc("__KEY__")
    columns = list(df_keyed.columns)

    for row_tuple in df_keyed.itertuples(index=False, name=None):
        key = row_tuple[key_col_idx]
        row_dict = {columns[i]: row_tuple[i] for i in range(len(columns))}
        if key in groups:
            groups[key].append(row_dict)
        else:
            groups[key] = [row_dict]

    return groups


def compare_datasets(old_df, new_df):
    """
    Compare two DataFrames using 9-column business identity key.

    Optimized:
      - Single groupby → dict conversion per dataset
      - Single pass over common keys
      - Pre-converted rows to dicts for O(1) access
      - DEBUG_MODE controls diagnostic verbosity

    Returns
    -------
    (modified_df, new_only_df, deleted_df, nochange_df, comp_diagnostics)
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
    old_keyed, old_key_diags = build_business_identity_key(old_norm, collect_debug=DEBUG_MODE)
    new_keyed, new_key_diags = build_business_identity_key(new_norm, collect_debug=DEBUG_MODE)

    comp_diagnostics["old_identity"] = old_key_diags
    comp_diagnostics["new_identity"] = new_key_diags

    # ── Build group dicts ONCE — O(1) lookups for entire comparison ────────────
    old_groups = _build_group_dict(old_keyed)
    new_groups = _build_group_dict(new_keyed)

    # ── Set math on unique key sets ────────────────────────────────────────────
    old_keys = set(old_groups.keys())
    new_keys = set(new_groups.keys())

    common_keys   = old_keys & new_keys
    new_only_keys = new_keys - old_keys
    deleted_keys  = old_keys - new_keys

    comp_diagnostics["common_key_count"] = len(common_keys)
    comp_diagnostics["new_only_key_count"] = len(new_only_keys)
    comp_diagnostics["deleted_key_count"] = len(deleted_keys)

    # ── Determine non-key columns to compare ──────────────────────────────────
    old_col_set = set(old_keyed.columns)
    compare_cols = [c for c in new_keyed.columns
                    if c in old_col_set
                    and c != "__KEY__"
                    and c.upper() not in _SKIP_COMPARE]

    # ── SINGLE PASS: classify common keys ─────────────────────────────────────
    modified_rows = []
    nochange_rows = []
    extra_new_rows = []
    extra_deleted_rows = []

    for key in common_keys:
        old_row_list = old_groups[key]  # O(1) dict lookup
        new_row_list = new_groups[key]  # O(1) dict lookup

        min_len = min(len(old_row_list), len(new_row_list))

        # Positional matching: compare first-to-first, second-to-second
        for i in range(min_len):
            old_dict = old_row_list[i]
            new_dict = new_row_list[i]

            changes = _detect_changes_dict(old_dict, new_dict, compare_cols)

            row_data = {k: v for k, v in new_dict.items() if k != "__KEY__"}

            if changes:
                row_data["CHANGES"] = changes
                modified_rows.append(row_data)
            else:
                nochange_rows.append(row_data)

        # Extra new rows (more in NEW than OLD for this key)
        for i in range(min_len, len(new_row_list)):
            row_data = {k: v for k, v in new_row_list[i].items() if k != "__KEY__"}
            extra_new_rows.append(row_data)

        # Extra deleted rows (more in OLD than NEW for this key)
        for i in range(min_len, len(old_row_list)):
            row_data = {k: v for k, v in old_row_list[i].items() if k != "__KEY__"}
            extra_deleted_rows.append(row_data)

    # ── Build output DataFrames ────────────────────────────────────────────────
    modified_df = pd.DataFrame(modified_rows) if modified_rows else pd.DataFrame()
    nochange_df = pd.DataFrame(nochange_rows) if nochange_rows else pd.DataFrame()

    # New-only: keys exclusively in NEW + extra rows from common keys
    new_only_rows = []
    for key in new_only_keys:
        for row_dict in new_groups[key]:
            new_only_rows.append({k: v for k, v in row_dict.items() if k != "__KEY__"})
    new_only_rows.extend(extra_new_rows)
    new_only_df = pd.DataFrame(new_only_rows) if new_only_rows else pd.DataFrame()

    # Deleted: keys exclusively in OLD + extra rows from common keys
    deleted_rows = []
    for key in deleted_keys:
        for row_dict in old_groups[key]:
            deleted_rows.append({k: v for k, v in row_dict.items() if k != "__KEY__"})
    deleted_rows.extend(extra_deleted_rows)
    deleted_df = pd.DataFrame(deleted_rows) if deleted_rows else pd.DataFrame()

    comp_diagnostics["modified_count"] = len(modified_df)
    comp_diagnostics["nochange_count"] = len(nochange_df)
    comp_diagnostics["new_count"] = len(new_only_df)
    comp_diagnostics["deleted_count"] = len(deleted_df)
    comp_diagnostics["extra_new_from_common"] = len(extra_new_rows)
    comp_diagnostics["extra_deleted_from_common"] = len(extra_deleted_rows)

    return modified_df, new_only_df, deleted_df, nochange_df, comp_diagnostics
