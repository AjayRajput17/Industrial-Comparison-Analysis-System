import pandas as pd
import json

def format_changes(changes_value):
    """Convert CHANGES dict to a readable multiline string: 'Field: old → new'"""
    if isinstance(changes_value, dict):
        if not changes_value:
            return ""
        lines = [f"{col}: {diff}" for col, diff in changes_value.items()]
        return "\n".join(lines)
    if isinstance(changes_value, str):
        try:
            parsed = json.loads(changes_value.replace("'", '"'))
            return format_changes(parsed)
        except Exception:
            return changes_value
    return str(changes_value) if changes_value else ""

def sanitize_for_excel(df):
    """Sanitize a dataframe so every cell is Excel-safe without breaking dtypes."""
    safe_df = df.copy()
    for col in safe_df.columns:
        col_upper = str(col).upper()
        
        # Preserve numbers; strip timezones from dates to prevent openpyxl crash
        if pd.api.types.is_numeric_dtype(safe_df[col]):
            continue
        if pd.api.types.is_datetime64_any_dtype(safe_df[col]):
            if getattr(safe_df[col].dt, 'tz', None) is not None:
                safe_df[col] = safe_df[col].dt.tz_localize(None)
            continue
            
        if col_upper == "CHANGES":
            safe_df[col] = safe_df[col].apply(format_changes)
        elif col_upper == "COMMENTS":
            safe_df[col] = safe_df[col].fillna("").astype(str)
        else:
            safe_df[col] = safe_df[col].apply(
                lambda v: json.dumps(v, ensure_ascii=False)
                if isinstance(v, (dict, list, tuple, set))
                else v
            )
    return safe_df
