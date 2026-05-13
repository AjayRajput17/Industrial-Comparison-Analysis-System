"""
Business Filters Module.
Applies manager-confirmed filtering rules on the RAW MBOM data
BEFORE field mapping and deduplication.
"""

import pandas as pd
from config.business_rules import (
    VALID_PART_STATUS,
    VALID_TORQUE_SAFETY,
    TORQUE_FILTER_FIELD,
    TORQUE_THRESHOLD,
    KEEP_ZERO_TORQUE,
    RAW_PART_STATUS_PATH,
    RAW_TORQUE_SAFETY_PATH,
    RAW_TRGT_RESIDUAL_PATH,
)


def _resolve_column(df, target_path):
    """Find a column in the DataFrame matching the target multi-index path."""
    # Normalize the target for comparison
    norm_target = tuple(" ".join(str(p).upper().strip().split()) for p in target_path)
    for col in df.columns:
        if isinstance(col, tuple):
            norm_col = tuple(" ".join(str(p).upper().strip().split()) for p in col)
            if norm_col == norm_target:
                return col
        else:
            if " ".join(str(col).upper().strip().split()) == norm_target[-1]:
                return col
    return None


def filter_part_status(df, diagnostics):
    """Keep only rows where PART STATUS is in VALID_PART_STATUS (e.g. 'R')."""
    col = _resolve_column(df, RAW_PART_STATUS_PATH)
    before = len(df)

    if col is not None:
        mask = df[col].astype(str).str.strip().str.upper().isin(
            [v.upper() for v in VALID_PART_STATUS]
        )
        df = df[mask].reset_index(drop=True)
        diagnostics["filter_part_status_col"] = str(col)
    else:
        diagnostics["filter_part_status_col"] = "NOT FOUND — skipped"

    after = len(df)
    diagnostics["rows_before_part_status_filter"] = before
    diagnostics["rows_after_part_status_filter"] = after
    diagnostics["rows_removed_part_status"] = before - after
    return df, diagnostics


def filter_torque_safety(df, diagnostics):
    """Keep only rows where TORQUE SAFETY is Y or N (remove blank and '?')."""
    col = _resolve_column(df, RAW_TORQUE_SAFETY_PATH)
    before = len(df)

    if col is not None:
        mask = df[col].astype(str).str.strip().str.upper().isin(
            [v.upper() for v in VALID_TORQUE_SAFETY]
        )
        df = df[mask].reset_index(drop=True)
        diagnostics["filter_torque_safety_col"] = str(col)
    else:
        diagnostics["filter_torque_safety_col"] = "NOT FOUND — skipped"

    after = len(df)
    diagnostics["rows_before_torque_safety_filter"] = before
    diagnostics["rows_after_torque_safety_filter"] = after
    diagnostics["rows_removed_torque_safety"] = before - after
    return df, diagnostics


def filter_trgt(df, diagnostics):
    """
    Apply TRGT business filter on RESIDUAL TRGT.
    Rule: Keep TRGT == 0 OR TRGT >= 5. Remove 0 < TRGT < 5.
    """
    col = _resolve_column(df, RAW_TRGT_RESIDUAL_PATH)
    before = len(df)

    if col is not None:
        trgt_numeric = pd.to_numeric(df[col], errors="coerce").fillna(0)
        # Keep: value == 0 OR value >= TORQUE_THRESHOLD
        # Remove: 0 < value < TORQUE_THRESHOLD
        mask = (trgt_numeric == 0) | (trgt_numeric >= TORQUE_THRESHOLD)
        df = df[mask].reset_index(drop=True)
        diagnostics["filter_trgt_col"] = str(col)
    else:
        diagnostics["filter_trgt_col"] = "NOT FOUND — skipped"

    after = len(df)
    diagnostics["rows_before_trgt_filter"] = before
    diagnostics["rows_after_trgt_filter"] = after
    diagnostics["rows_removed_trgt"] = before - after
    return df, diagnostics


def apply_all_business_filters(df, diagnostics=None):
    """
    Apply all business filters in the correct order.
    Returns the filtered DataFrame and updated diagnostics.
    """
    if diagnostics is None:
        diagnostics = {}

    diagnostics["rows_before_all_filters"] = len(df)

    # 1. PART STATUS = R
    df, diagnostics = filter_part_status(df, diagnostics)

    # 2. TORQUE SAFETY = Y or N
    df, diagnostics = filter_torque_safety(df, diagnostics)

    # 3. TRGT filter (keep 0, remove 0 < x < 5)
    df, diagnostics = filter_trgt(df, diagnostics)

    diagnostics["rows_after_all_filters"] = len(df)
    diagnostics["total_rows_filtered_out"] = (
        diagnostics["rows_before_all_filters"] - diagnostics["rows_after_all_filters"]
    )

    return df, diagnostics
