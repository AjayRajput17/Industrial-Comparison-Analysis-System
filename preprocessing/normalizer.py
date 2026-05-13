import pandas as pd
import re

def clean_hidden_characters(val: str) -> str:
    """Removes invisible unicode characters and zero-width spaces."""
    if not isinstance(val, str):
        val = str(val)
    # Remove control characters and non-printable unicode
    val = re.sub(r'[\x00-\x1F\x7F-\x9F\u200B-\u200D\uFEFF]', '', val)
    return val

def normalize_columns(columns: list) -> list:
    """
    Normalizes a list of column names (or tuples for MultiIndex).
    1. remove hidden characters
    2. uppercase
    3. trim trailing/leading spaces
    4. removing duplicate spaces
    """
    normalized = []
    for col in columns:
        if isinstance(col, tuple):
            norm_tuple = tuple(
                " ".join(clean_hidden_characters(str(part)).upper().strip().split()) if pd.notna(part) else "UNNAMED"
                for part in col
            )
            normalized.append(norm_tuple)
        else:
            if pd.isna(col):
                normalized.append("UNNAMED")
                continue
            c = clean_hidden_characters(str(col)).upper().strip()
            normalized.append(c)
    return normalized

def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes the columns of a dataframe directly."""
    df.columns = normalize_columns(df.columns)
    return df
