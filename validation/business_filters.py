"""
Business Filters Module.
Applies manager-confirmed filtering rules on the RAW MBOM data
BEFORE field mapping and deduplication.

OPTIMIZED: Precomputes combined boolean masks and applies single slice.
"""

import pandas as pd
import numpy as np
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


def apply_all_business_filters(df, diagnostics=None):
    """
    Apply all business filters using precomputed combined mask (single slice).
    Returns the filtered DataFrame and updated diagnostics.
    """
    if diagnostics is None:
        diagnostics = {}

    total_before = len(df)
    diagnostics["rows_before_all_filters"] = total_before

    # Start with an all-True mask
    combined_mask = pd.Series(True, index=df.index)

    # ── 1. PART STATUS = R ────────────────────────────────────────────────────
    ps_col = _resolve_column(df, RAW_PART_STATUS_PATH)
    if ps_col is not None:
        ps_mask = df[ps_col].astype(str).str.strip().str.upper().isin(
            [v.upper() for v in VALID_PART_STATUS]
        )
        diagnostics["filter_part_status_col"] = str(ps_col)
        diagnostics["rows_removed_part_status"] = int((~ps_mask).sum())
        combined_mask = combined_mask & ps_mask
    else:
        diagnostics["filter_part_status_col"] = "NOT FOUND — skipped"
        diagnostics["rows_removed_part_status"] = 0

    diagnostics["rows_before_part_status_filter"] = total_before
    diagnostics["rows_after_part_status_filter"] = int(combined_mask.sum())

    # ── 2. TORQUE SAFETY = Y or N ────────────────────────────────────────────
    ts_col = _resolve_column(df, RAW_TORQUE_SAFETY_PATH)
    rows_before_ts = int(combined_mask.sum())
    if ts_col is not None:
        ts_mask = df[ts_col].astype(str).str.strip().str.upper().isin(
            [v.upper() for v in VALID_TORQUE_SAFETY]
        )
        diagnostics["filter_torque_safety_col"] = str(ts_col)
        # Count removals only among rows that survived previous filter
        diagnostics["rows_removed_torque_safety"] = int((combined_mask & ~ts_mask).sum())
        combined_mask = combined_mask & ts_mask
    else:
        diagnostics["filter_torque_safety_col"] = "NOT FOUND — skipped"
        diagnostics["rows_removed_torque_safety"] = 0

    diagnostics["rows_before_torque_safety_filter"] = rows_before_ts
    diagnostics["rows_after_torque_safety_filter"] = int(combined_mask.sum())

    # ── 3. TRGT filter (keep 0 and ≥5, remove 0 < x < 5) ────────────────────
    trgt_col = _resolve_column(df, RAW_TRGT_RESIDUAL_PATH)
    rows_before_trgt = int(combined_mask.sum())
    if trgt_col is not None:
        trgt_numeric = pd.to_numeric(df[trgt_col], errors="coerce").fillna(0)
        trgt_mask = (trgt_numeric == 0) | (trgt_numeric >= TORQUE_THRESHOLD)
        diagnostics["filter_trgt_col"] = str(trgt_col)
        diagnostics["rows_removed_trgt"] = int((combined_mask & ~trgt_mask).sum())
        combined_mask = combined_mask & trgt_mask
    else:
        diagnostics["filter_trgt_col"] = "NOT FOUND — skipped"
        diagnostics["rows_removed_trgt"] = 0

    diagnostics["rows_before_trgt_filter"] = rows_before_trgt
    diagnostics["rows_after_trgt_filter"] = int(combined_mask.sum())

    # ── Apply single combined filter ──────────────────────────────────────────
    df = df[combined_mask].reset_index(drop=True)

    diagnostics["rows_after_all_filters"] = len(df)
    diagnostics["total_rows_filtered_out"] = total_before - len(df)

    return df, diagnostics
