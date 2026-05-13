"""
Business Identity Validator.
Validates the 9-column business identity key for collisions.
Reports but does NOT automatically deduplicate.
"""

import pandas as pd


def validate_business_key_uniqueness(df, key_column="__KEY__"):
    """
    Check whether the 9-column identity still produces collisions.

    Parameters
    ----------
    df : DataFrame with __KEY__ column.

    Returns
    -------
    dict with collision statistics.
    """
    diagnostics = {}

    if key_column not in df.columns:
        diagnostics["status"] = "No __KEY__ column found"
        return diagnostics

    key_counts = df[key_column].value_counts()
    duplicates = key_counts[key_counts > 1]

    diagnostics["total_unique_keys"] = len(key_counts)
    diagnostics["duplicate_key_count"] = len(duplicates)
    diagnostics["total_colliding_rows"] = int(duplicates.sum()) if len(duplicates) > 0 else 0

    if not duplicates.empty:
        diagnostics["sample_duplicate_keys"] = duplicates.head(5).to_dict()
        diagnostics["status"] = f"WARNING: {len(duplicates)} identity collisions detected"
    else:
        diagnostics["status"] = "All business identities are unique"

    return diagnostics


def export_duplicate_identity_groups(df, key_column="__KEY__", output_path=None):
    """
    Export duplicate business identity groups to an Excel file for debugging.

    Parameters
    ----------
    df : DataFrame with __KEY__ column.
    output_path : str, optional. If None, returns bytes.

    Returns
    -------
    bytes or None (if written to file).
    """
    import io

    if key_column not in df.columns:
        return None

    key_counts = df[key_column].value_counts()
    duplicate_keys = key_counts[key_counts > 1].index.tolist()

    if not duplicate_keys:
        return None

    duplicate_rows = df[df[key_column].isin(duplicate_keys)].sort_values(key_column)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        duplicate_rows.to_excel(writer, index=False, sheet_name="Duplicate Groups")

        # Summary sheet
        summary = pd.DataFrame({
            "Business Identity Key": duplicate_keys[:100],
            "Occurrence Count": [key_counts[k] for k in duplicate_keys[:100]],
        })
        summary.to_excel(writer, index=False, sheet_name="Summary")

    if output_path:
        with open(output_path, "wb") as f:
            f.write(output.getvalue())
        return None

    return output.getvalue()
