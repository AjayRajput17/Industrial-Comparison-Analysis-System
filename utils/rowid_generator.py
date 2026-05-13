import pandas as pd
from config.rowid_config import ROW_ID_COLUMNS

def generate_row_id(row: pd.Series, columns: list = None) -> str:
    """
    Generates a deterministic Row ID combining configured fields using a pipe '|'.
    Handles missing values safely.
    """
    if columns is None:
        columns = ROW_ID_COLUMNS
        
    parts = []
    for col in columns:
        if col in row.index and pd.notna(row[col]):
            val = str(row[col]).strip()
            # Special handling for floats that are actually integers (e.g. 2025.0 -> '2025')
            if val.endswith(".0"):
                val = val[:-2]
            parts.append(val)
        else:
            parts.append("") # Keep it blank but maintain the pipe separator count
            
    return "|".join(parts)

def apply_row_ids(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    """Applies the generate_row_id logic to an entire Dataframe."""
    if df.empty:
        df["ROW ID"] = []
    else:
        df["ROW ID"] = df.apply(lambda row: generate_row_id(row, columns), axis=1)
    return df
