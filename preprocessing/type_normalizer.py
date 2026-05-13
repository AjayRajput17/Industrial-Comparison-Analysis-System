import pandas as pd
import numpy as np

def handle_sentinel_values(df: pd.DataFrame) -> pd.DataFrame:
    """Replace known sentinel values like '?' with NaN."""
    # Replace '?' specifically since it's a known sentinel in MIN etc.
    return df.replace('?', np.nan)

def normalize_null_values(df: pd.DataFrame) -> pd.DataFrame:
    """Convert empty strings, 'NULL', 'None' to NaN."""
    # Replace whitespace-only strings with NaN
    df = df.replace(r'^\s*$', np.nan, regex=True)
    # Replace common string null representations
    df = df.replace(["NULL", "None", "null", "none", "NULL", "NONE"], np.nan)
    return df

def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    float_cols = ["MIN", "TRGT", "MAX", "TORQUE SNUG TARGET"]
    int_cols = ["TRGT2", "QUANTITY"] # adding quantity generally
    
    for col in df.columns:
        col_name = str(col).strip().upper()
        if col_name in float_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif col_name in int_cols:
            # use pandas nullable integer type
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df

def normalize_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = ["DECISION DATE"]
    for col in df.columns:
        col_name = str(col).strip().upper()
        if col_name in date_cols:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    df = handle_sentinel_values(df)
    df = normalize_null_values(df)
    df = normalize_numeric_columns(df)
    df = normalize_date_columns(df)
    return df
