"""
Business Deduplication Validator.
Manager-confirmed: Use BUSINESS FIELD SUBSET matching, NOT full-row equality.
"""

import pandas as pd
from config.deduplication_config import DEDUP_COLUMNS


def detect_duplicates(df: pd.DataFrame) -> dict:
    """
    Detects rows that are business duplicates using the DEDUP_COLUMNS subset.
    """
    diagnostics = {}
    total_rows = len(df)

    # Find which DEDUP_COLUMNS actually exist in the dataframe
    available_cols = [c for c in DEDUP_COLUMNS if c in df.columns]
    diagnostics["dedup_columns_used"] = available_cols

    if not available_cols:
        diagnostics["total_rows_pre_dedupe"] = total_rows
        diagnostics["exact_duplicates_to_remove"] = 0
        diagnostics["dedup_status"] = "No dedup columns found — skipped"
        return diagnostics

    # duplicated(keep='first') flags all but the first instance
    duplicates_to_remove = df[df.duplicated(subset=available_cols, keep='first')]

    diagnostics["total_rows_pre_dedupe"] = total_rows
    diagnostics["exact_duplicates_to_remove"] = len(duplicates_to_remove)

    return diagnostics


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Safely removes business duplicate rows using DEDUP_COLUMNS subset.
    Preserves unique business rows and row ordering.
    """
    available_cols = [c for c in DEDUP_COLUMNS if c in df.columns]
    if not available_cols:
        return df
    return df.drop_duplicates(subset=available_cols, keep='first').reset_index(drop=True)


def validate_rowid_uniqueness(df: pd.DataFrame) -> dict:
    """
    Validates ROW ID uniqueness AFTER deduplication.
    Counts remaining duplicate Row IDs (which indicate conflicting records).
    """
    diagnostics = {}

    if "ROW ID" not in df.columns:
        diagnostics["validation_status"] = "No ROW ID column to validate"
        return diagnostics

    rowid_counts = df["ROW ID"].value_counts()
    conflicting_rowids = rowid_counts[rowid_counts > 1]

    diagnostics["total_rows_post_dedupe"] = len(df)
    diagnostics["conflicting_rowids_remaining"] = len(conflicting_rowids)

    if not conflicting_rowids.empty:
        diagnostics["sample_conflicting_rowids"] = conflicting_rowids.head(5).index.tolist()
        diagnostics["validation_status"] = "WARNING: Conflicting rows found (same ROW ID, different business data)"
    else:
        diagnostics["validation_status"] = "All ROW IDs are now 100% unique."

    return diagnostics
