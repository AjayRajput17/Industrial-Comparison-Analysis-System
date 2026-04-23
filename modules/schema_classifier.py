import pandas as pd

def _get_part_no(data_dict):
    """Extract part no safely from dictionary"""
    for candidate in ('part no', 'part number', 'part_no', 'partno'):
        if candidate in data_dict:
            val = data_dict[candidate]
            if val is not None and str(val).strip().upper() not in ('', 'NAN', 'NONE', 'NAT', '<NA>', 'NULL'):
                return str(val).strip().upper()
    return None

def classify_transformed(records):
    """
    Classifies the structured {"old": {...}, "new": {...}} records into
    modified, new, and deleted DataFrames.
    """
    modified_rows = []
    new_rows = []
    deleted_rows = []
    
    for rec in records:
        old_dict = rec["old"]
        new_dict = rec["new"]
        
        old_part = _get_part_no(old_dict)
        new_part = _get_part_no(new_dict)
        
        # If we couldn't resolve part numbers but the record has data, fallback safely
        # or discard if completely invalid.
        if not old_part and not new_part:
            continue
            
        if old_part and new_part:
            # Modified
            changes = {}
            all_keys = set(old_dict.keys()) | set(new_dict.keys())
            
            for k in all_keys:
                if k in ('part no', 'part number', 'part_no', 'partno'):
                    continue
                    
                v_old = old_dict.get(k)
                v_new = new_dict.get(k)
                
                old_str = "" if pd.isna(v_old) or v_old is None else str(v_old).strip()
                new_str = "" if pd.isna(v_new) or v_new is None else str(v_new).strip()
                
                if old_str != new_str:
                    changes[k] = f"{old_str} → {new_str}"
                    
            if changes:
                combined = new_dict.copy()
                combined["CHANGES"] = changes
                modified_rows.append(combined)
            
        elif not old_part and new_part:
            # New
            new_rows.append(new_dict)
        elif old_part and not new_part:
            # Deleted
            deleted_rows.append(old_dict)
            
    return pd.DataFrame(modified_rows), pd.DataFrame(new_rows), pd.DataFrame(deleted_rows)
