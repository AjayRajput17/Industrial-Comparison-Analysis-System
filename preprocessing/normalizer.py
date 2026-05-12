import pandas as pd

def normalize_columns(columns: list) -> list:
    """
    Normalizes a list of column names (or tuples for MultiIndex).
    1. uppercase
    2. trim trailing/leading spaces
    3. removing duplicate spaces
    """
    normalized = []
    for col in columns:
        if isinstance(col, tuple):
            norm_tuple = tuple(
                " ".join(str(part).upper().strip().split()) if pd.notna(part) else "UNNAMED" 
                for part in col
            )
            normalized.append(norm_tuple)
        else:
            if pd.isna(col):
                normalized.append("UNNAMED")
                continue
            c = str(col).upper().strip()
            c = " ".join(c.split())
            normalized.append(c)
    return normalized

def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes the columns of a dataframe directly."""
    df.columns = normalize_columns(df.columns)
    return df
