import pandas as pd

def detect_exact_duplicates(df: pd.DataFrame) -> dict:
    """
    Detects rows that are exact duplicates across ALL columns.
    Returns diagnostics about the duplicates found.
    """
    diagnostics = {}
    total_rows = len(df)
    
    # df.duplicated() with keep=False flags all instances of duplicates
    # df.duplicated() with keep='first' flags all but the first instance
    exact_duplicates = df[df.duplicated(keep=False)]
    duplicates_to_remove = df[df.duplicated(keep='first')]
    
    diagnostics["total_rows_pre_dedupe"] = total_rows
    diagnostics["total_duplicate_rows_found"] = len(exact_duplicates)
    diagnostics["exact_duplicates_to_remove"] = len(duplicates_to_remove)
    
    if "ROW ID" in df.columns:
        duplicate_row_ids = duplicates_to_remove["ROW ID"].unique().tolist()
        diagnostics["duplicate_row_ids_count"] = len(duplicate_row_ids)
    
    return diagnostics

def remove_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Safely removes ONLY fully identical duplicate rows.
    Preserves unique business rows and row ordering.
    """
    # Using drop_duplicates() without subset ensures ALL columns must match
    return df.drop_duplicates(keep='first').reset_index(drop=True)

def validate_rowid_uniqueness(df: pd.DataFrame) -> dict:
    """
    Validates uniqueness AFTER deduplication.
    Counts remaining duplicate Row IDs (which indicate conflicting records).
    """
    diagnostics = {}
    
    if "ROW ID" not in df.columns:
        diagnostics["status"] = "No ROW ID column to validate"
        return diagnostics
        
    rowid_counts = df["ROW ID"].value_counts()
    conflicting_rowids = rowid_counts[rowid_counts > 1]
    
    diagnostics["total_rows_post_dedupe"] = len(df)
    diagnostics["conflicting_rowids_remaining"] = len(conflicting_rowids)
    
    if not conflicting_rowids.empty:
        diagnostics["sample_conflicting_rowids"] = conflicting_rowids.head(5).index.tolist()
        diagnostics["status"] = "WARNING: Conflicting rows found (same ROW ID, different business data)"
    else:
        diagnostics["status"] = "✅ All ROW IDs are now 100% unique."
        
    return diagnostics
