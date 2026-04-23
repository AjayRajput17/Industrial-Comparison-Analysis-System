import pandas as pd

def transform_old_new(df):
    """
    Transforms schema-based rows where old_data.* and new_data.* 
    are in the same row into structured list of dictionaries.
    """
    records = []
    
    for _, row in df.iterrows():
        old_dict = {}
        new_dict = {}
        
        for col, val in row.items():
            if pd.isna(val):
                val = None  # Convert numpy/pandas NaN to Python None
                
            col_lower = str(col).strip().lower()
            
            if col_lower.startswith('old_data.'):
                key = col_lower.replace('old_data.', '', 1).strip()
                old_dict[key] = val
            elif col_lower.startswith('new_data.'):
                key = col_lower.replace('new_data.', '', 1).strip()
                new_dict[key] = val
                
        # Only append if at least there is an indication of part in either old or new
        # Sometimes there's completely empty rows.
        if old_dict or new_dict:
            records.append({"old": old_dict, "new": new_dict})
            
    return records
