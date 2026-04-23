
import pandas as pd
from modules.preprocessing import detect_old_prefix


def _normalize(val):
    """Return True if val is considered present/non-null."""
    return str(val).strip().upper() not in ('', 'NAN', 'NONE', 'NAT', '<NA>', 'NULL', 'NAT')


def _strip_prefix(df, prefix):
    """
    Given a dataframe that has columns like 'Prefix.COL_NAME',
    return a renamed dataframe using only COL_NAME as column headers.
    Only keep columns that start with the prefix.
    """
    prefix_dot = prefix + '.'
    prefixed_cols = {col: col[len(prefix_dot):] for col in df.columns
                     if col.startswith(prefix_dot)}
    if not prefixed_cols:
        return pd.DataFrame()
    return df[list(prefixed_cols.keys())].rename(columns=prefixed_cols)


def _find_status_column(df, candidates):
    """Find first column in df whose lowered name contains any candidate string."""
    for col in df.columns:
        col_l = str(col).strip().lower()
        for c in candidates:
            if c in col_l:
                return col
    return None


def separate_data(df, structure):
    df = df.copy()

    # ─────────────────────────────────────────────────────────────────────────
    # FORMAT C  — status_dual:
    #   Added rows  → data in plain columns
    #   Deleted rows → data in prefixed columns (dynamic prefix, auto-detected)
    # ─────────────────────────────────────────────────────────────────────────
    if structure == "status_dual":
        added_col   = _find_status_column(df, ['added rows', 'added row'])
        deleted_col = _find_status_column(df, ['deleted rows', 'deleted row'])

        # Identify Added rows ─ status value contains "add" (case-insensitive)
        if added_col:
            added_mask = df[added_col].astype(str).str.strip().str.lower().str.contains(
                'add', na=False)
            added_df = df[added_mask].copy()
        else:
            added_df = pd.DataFrame()

        # Identify Deleted rows ─ status value contains "delet"
        if deleted_col:
            deleted_mask = df[deleted_col].astype(str).str.strip().str.lower().str.contains(
                'delet', na=False)
            deleted_raw = df[deleted_mask].copy()
        else:
            deleted_raw = pd.DataFrame()

        # Auto-detect the dynamic prefix (e.g. "Old data(07-07-2025)")
        prefix = detect_old_prefix(df)

        # Build normalized deleted_df:
        # • Pull data from prefixed columns (strip prefix → plain col names)
        # • Fill any still-missing plain fields from the prefixed columns
        if prefix and not deleted_raw.empty:
            deleted_df = _strip_prefix(deleted_raw, prefix)
        else:
            # No prefix found — just use the raw deleted rows as-is
            deleted_df = deleted_raw.copy()

        # Drop status / comparison helper columns from both dataframes
        helper_patterns = ['added rows', 'added row', 'deleted rows', 'deleted row',
                           'torque changes', 'qty check', 'phy dec check', 'cn check',
                           'row id', 'tc check', 'row_id']

        def _drop_helpers(frame):
            drop_cols = [c for c in frame.columns
                         if str(c).strip().lower() in helper_patterns
                         or any(p in str(c).strip().lower() for p in helper_patterns)]
            return frame.drop(columns=drop_cols, errors='ignore')

        added_df   = _drop_helpers(added_df)
        deleted_df = _drop_helpers(deleted_df)

        return added_df, deleted_df

    # ─────────────────────────────────────────────────────────────────────────
    # FORMAT A  — single "status" column (Added / Deleted in same column)
    # ─────────────────────────────────────────────────────────────────────────
    if structure == "status":
        df.columns = [str(c).strip().lower() for c in df.columns]
        status_values = df['status'].astype(str).str.strip().str.lower()

        added_tokens   = {'added', 'add', 'new', 'created', 'inserted'}
        deleted_tokens = {'deleted', 'delete', 'removed', 'remove'}

        added_mask   = status_values.isin(added_tokens)
        deleted_mask = status_values.isin(deleted_tokens)

        return df[added_mask], df[deleted_mask]

    # ─────────────────────────────────────────────────────────────────────────
    # FORMAT: old value / new value columns
    # ─────────────────────────────────────────────────────────────────────────
    if structure == "old_new":
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df[df['old value'].isna()], df[df['new value'].isna()]

    # Fallback: unknown structure
    return df, df.iloc[0:0]
