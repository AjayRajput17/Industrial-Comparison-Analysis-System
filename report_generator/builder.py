import pandas as pd
from preprocessing.structure_analyzer import detect_header_row, analyze_multilevel_headers
from preprocessing.normalizer import normalize_dataframe_columns
from utils.rowid_generator import apply_row_ids
from config.column_mapping import COLUMN_MAPPING

def extract_target_schema(reference_file_bytes: bytes) -> list:
    """Extracts column sequence directly from the gold template."""
    import io
    df_ref = pd.read_excel(io.BytesIO(reference_file_bytes), nrows=0)
    # The gold template might have trailing spaces, normalizer strips them to match our flow
    from preprocessing.normalizer import normalize_columns
    return normalize_columns(df_ref.columns.tolist())

def build_business_report_from_raw(raw_file_bytes: bytes, reference_file_bytes: bytes) -> tuple[pd.DataFrame, dict]:
    """
    Executes the strict MBOM to Golden Template generation flow using Hierarchical Header paths.
    """
    diagnostics = {}
    
    # 1. Detect target reference schema
    target_columns = extract_target_schema(reference_file_bytes)
    diagnostics["target_columns_count"] = len(target_columns)
    
    # 2. Structure Analyzer: Detect Multi-Level actual header row and load DF
    header_idx, df_raw = detect_header_row(raw_file_bytes)
    diagnostics["detected_header_row_index"] = header_idx
    
    # 3. Analyze and Print the MultiIndex hierarchy before normalizing
    raw_paths = analyze_multilevel_headers(df_raw)
    
    # 4. Normalizer: Clean the column names/tuples so they match exactly
    df_raw = normalize_dataframe_columns(df_raw)
    diagnostics["normalized_raw_columns"] = df_raw.columns.tolist()
    
    # Pre-process the raw columns into a searchable dictionary:
    # Keys = flat column names, Values = first matched column tuple
    flat_lookup = {}
    for col_tuple in df_raw.columns:
        if isinstance(col_tuple, tuple):
            leaf = str(col_tuple[-1])
            if leaf not in flat_lookup:
                flat_lookup[leaf] = col_tuple
        else:
             flat_lookup[str(col_tuple)] = col_tuple
    
    # 5. Hierarchical Field Mapping
    df_final = pd.DataFrame()
    matched_fields = []
    unmatched_fields = []
    
    for target_col in target_columns:
        if target_col == "ROW ID":
            continue # Handled by Row ID Engine
            
        mapped = False
        
        # Check if there is an explicit MultiIndex tuple rule for this column
        if target_col in COLUMN_MAPPING:
            rule_path = tuple(" ".join(str(part).upper().strip().split()) for part in COLUMN_MAPPING[target_col])
            
            # Find it strictly in the dataframe columns
            if rule_path in df_raw.columns:
                df_final[target_col] = df_raw[rule_path]
                matched_fields.append(f"{target_col} -> {rule_path}")
                mapped = True
        
        # Fallback to direct flat mapping using the leaf node
        if not mapped:
            if target_col in flat_lookup:
                best_tuple = flat_lookup[target_col]
                df_final[target_col] = df_raw[best_tuple]
                matched_fields.append(f"{target_col} -> {best_tuple} (Flat Fallback)")
                mapped = True
        
        if not mapped:
            df_final[target_col] = "" # Fill missing target field with empty string
            unmatched_fields.append(target_col)
            
    # 6. Row ID Generation Engine
    # Only run if ROW ID is requested by the target template
    if "ROW ID" in target_columns:
        df_final = apply_row_ids(df_final)
        
    diagnostics["matched_fields"] = matched_fields
    diagnostics["unmatched_fields"] = unmatched_fields
    
    # Ensure final ordering strictly matches the template order 
    # (Because apply_row_ids puts it at the end, so reorder completely)
    final_ordered_columns = [col for col in target_columns if col in df_final.columns]
    df_final = df_final[final_ordered_columns]
    
    diagnostics["final_report_schema"] = df_final.columns.tolist()
    diagnostics["rows_generated"] = len(df_final)

    return df_final, diagnostics
