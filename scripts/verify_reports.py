import pandas as pd
import numpy as np
import sys
import argparse

def normalize_compare_values(val):
    """Normalize values for strict comparison."""
    if pd.isna(val) or val == "":
        return "<NULL>"
    if isinstance(val, (int, float)):
        # Round floats to 2 decimal places to prevent floating point mismatch
        return str(round(float(val), 2))
    # Standardize strings
    return str(val).strip().upper()

def verify_reports(py_report_path, macro_report_path, key_column="ROW ID"):
    """
    Comprehensively compare the Python-generated Report against the Macro-generated Report.
    """
    print("=" * 60)
    print("🔍 REPORT VERIFICATION TOOL")
    print("=" * 60)

    print(f"Loading Python Report : {py_report_path}")
    print(f"Loading Macro Report  : {macro_report_path}")
    
    try:
        df_py = pd.read_excel(py_report_path)
        df_mac = pd.read_excel(macro_report_path)
    except Exception as e:
        print(f"❌ Error loading files: {e}")
        sys.exit(1)

    # 1. SCHEMA COMPARISON
    print("\n[1] Schema Comparison --------------------------------------")
    py_cols = list(df_py.columns)
    mac_cols = list(df_mac.columns)
    
    # Upper and strip spaces for baseline checks
    df_py.columns = [str(c).strip().upper() for c in py_cols]
    df_mac.columns = [str(c).strip().upper() for c in mac_cols]
    
    py_cols_clean = list(df_py.columns)
    mac_cols_clean = list(df_mac.columns)

    missing_in_py = set(mac_cols_clean) - set(py_cols_clean)
    missing_in_mac = set(py_cols_clean) - set(mac_cols_clean)

    if not missing_in_py and not missing_in_mac:
        print("✅ Column names and schema match perfectly.")
    else:
        print("❌ Schema mismatch detected!")
        if missing_in_py: print(f"   Missing in Python: {missing_in_py}")
        if missing_in_mac: print(f"   Missing in Macro: {missing_in_mac}")
    
    if py_cols_clean == mac_cols_clean:
         print("✅ Column sequence/ordering matches perfectly.")
    else:
         print("⚠️ Column ordering differs between files.")

    # 2. ROW COMPARISON
    print("\n[2] Dimensions ---------------------------------------------")
    print(f"   Python Report Rows: {len(df_py)}")
    print(f"   Macro  Report Rows: {len(df_mac)}")
    
    # 3. DATA & TYPE COMPARISON
    print("\n[3] Deep Data Comparison -----------------------------------")
    if key_column not in df_py.columns or key_column not in df_mac.columns:
        print(f"⚠️ '{key_column}' not found. Cannot perform row-to-row deep comparison.")
        print("Ensure 'ROW ID' is generated in both files for deep diffs.")
        sys.exit(0)

    # Convert to strings to ensure safe joins
    df_py[key_column] = df_py[key_column].astype(str).str.strip()
    df_mac[key_column] = df_mac[key_column].astype(str).str.strip()

    # Find common keys
    py_keys = set(df_py[key_column].unique())
    mac_keys = set(df_mac[key_column].unique())
    common_keys = py_keys & mac_keys
    
    print(f"   Keys in Python only : {len(py_keys - mac_keys)}")
    print(f"   Keys in Macro only  : {len(mac_keys - py_keys)}")
    print(f"   Common matching keys: {len(common_keys)}")

    if not common_keys:
        print("❌ No matching ROW IDs found. Cannot compare cell data.")
        sys.exit(1)

    print(f"\nAnalyzing data cells across {len(common_keys)} common rows...")
    
    # Set index for fast lookup
    df_py_common = df_py[df_py[key_column].isin(common_keys)].copy().set_index(key_column)
    df_mac_common = df_mac[df_mac[key_column].isin(common_keys)].copy().set_index(key_column)

    common_columns = set(py_cols_clean) & set(mac_cols_clean)
    
    mismatch_counts = {col: 0 for col in common_columns}
    mismatch_examples = []
    
    for row_id in common_keys:
        py_row = df_py_common.loc[row_id]
        mac_row = df_mac_common.loc[row_id]
        
        # If duplicated Row IDs exist, take the first one explicitly for comparison
        if isinstance(py_row, pd.DataFrame): py_row = py_row.iloc[0]
        if isinstance(mac_row, pd.DataFrame): mac_row = mac_row.iloc[0]
        
        for col in common_columns:
            py_val = normalize_compare_values(py_row.get(col))
            mac_val = normalize_compare_values(mac_row.get(col))
            
            if py_val != mac_val:
                mismatch_counts[col] += 1
                if len(mismatch_examples) < 10:  # Save up to 10 examples
                    mismatch_examples.append(f"Row {row_id} | Col [{col}]: Py='{py_val}' vs Mac='{mac_val}'")

    total_mismatches = sum(mismatch_counts.values())
    
    if total_mismatches == 0:
        print("\n✅ PERFECT DATA MATCH! All normalized cell values match identically.")
    else:
        print(f"\n❌ FOUND {total_mismatches} CELL MISMATCHES ACROSS COMMON COLUMNS:")
        for col, count in mismatch_counts.items():
            if count > 0:
                print(f"   - {col}: {count} differences")
                
        print("\n📝 Sample Mismatches:")
        for ex in mismatch_examples:
            print(f"   {ex}")
            
    print("\n=" * 60)
    print("Verification Completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Python export vs Macro export")
    parser.add_argument("python_excel", help="Path to the new Python generated excel report")
    parser.add_argument("macro_excel", help="Path to the old Macro generated excel report")
    parser.add_argument("--key", default="ROW ID", help="Shared unique identifier for row comparison")
    
    args = parser.parse_args()
    verify_reports(args.python_excel, args.macro_excel, args.key)
