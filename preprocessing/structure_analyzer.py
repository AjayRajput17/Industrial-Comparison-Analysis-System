import pandas as pd
import io

def analyze_multilevel_headers(df: pd.DataFrame):
    """
    Analyzes and prints multi-level header paths for debugging and mapping.
    """
    paths = []
    print("\n--- MULTI-LEVEL HEADER ANALYSIS ---")
    for col in df.columns:
        if isinstance(col, tuple):
            # Clean up Unnamed bits for printing readability
            clean_path = tuple(str(c) if not str(c).startswith("Unnamed:") else "---" for c in col)
            print(f"Path -> {clean_path}")
            paths.append(col)
        else:
            print(f"Flat -> {col}")
            paths.append((col,))
    print("----------------------------------\n")
    return paths

def detect_header_row(file_bytes: bytes, required_keywords: list = None) -> tuple[int, pd.DataFrame]:
    """
    Dynamically discovers the actual business header row by scanning for co-occuring keywords.
    Returns the index of the header row (0-indexed relative to Excel) and the reloaded DataFrame 
    via MultiIndex (using target_header_index - 2, target_header_index - 1, target_header_index).
    """
    if required_keywords is None:
        required_keywords = ["MODEL YEAR", "PART NO", "VEH FAM"]

    keywords_upper = [str(k).upper().strip() for k in required_keywords]
    
    # 1. Read the first chunk of rows raw to find the target keywords
    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, nrows=20)
    
    target_header_index = 0
    
    for i in range(len(df_raw)):
        # Convert the row to a list of strings, uppercase and trimmed
        row_values = []
        for val in df_raw.iloc[i].values:
            if pd.notna(val):
                cleaned = " ".join(str(val).upper().strip().split())
                row_values.append(cleaned)
        
        # Check if ALL required keywords exist in this row
        matches = sum(1 for kw in keywords_upper if kw in row_values)
        
        # If all core keywords exist in this row, we found our business header
        if matches == len(keywords_upper):
            target_header_index = i
            break
            
    # Calculate the multi-index header range (typically the business row and 2 rows above it)
    header_start = max(0, target_header_index - 2)
    header_list = list(range(header_start, target_header_index + 1))
    
    # 2. Reload the dataframe utilizing the discovered multi-level hierarchy
    df_actual = pd.read_excel(io.BytesIO(file_bytes), header=header_list)
    
    return target_header_index, df_actual
