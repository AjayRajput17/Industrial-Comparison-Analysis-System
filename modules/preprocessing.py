
def detect_structure(df):
    cols_lower = [str(col).strip().lower() for col in df.columns]

    # Format C: Two separate status columns "Added rows" / "Deleted Rows"
    # with data in plain columns for added and prefixed columns for deleted
    has_added_col  = any('added rows' in c or 'added row' in c for c in cols_lower)
    has_deleted_col = any('deleted rows' in c or 'deleted row' in c for c in cols_lower)
    if has_added_col or has_deleted_col:
        return "status_dual"

    # Format B: old_data.* / new_data.* in same row (generic prefix-in-same-row)
    if any(c.startswith('old_data.') for c in cols_lower):
        return "schema_based"

    # Format A: classic single "status" column
    if 'status' in cols_lower:
        return "status"

    # Format: old value / new value columns
    if 'old value' in cols_lower and 'new value' in cols_lower:
        return "old_new"

    return "unknown"


def detect_old_prefix(df):
    """
    Auto-detect the dynamic 'old data' column prefix.
    The prefix is the part before the first '.' in any column whose base name
    matches a plain column that already exists in the dataframe.

    Example: 'Old data(07-07-2025).PART NO' → prefix = 'Old data(07-07-2025)'
    Returns the prefix string (with trailing dot removed), or None if not found.
    """
    plain_cols_lower = set()
    dotted_cols = []

    for col in df.columns:
        col_str = str(col).strip()
        if '.' in col_str:
            dotted_cols.append(col_str)
        else:
            plain_cols_lower.add(col_str.lower())

    for col in dotted_cols:
        prefix, _, base = col.partition('.')
        if base.strip().lower() in plain_cols_lower:
            return prefix.strip()   # e.g. "Old data(07-07-2025)"

    return None
