"""
Headless verification: loads the real Excel file (sampling for speed)
and checks that the status_dual pipeline produces correct counts.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
from modules.preprocessing import detect_structure, detect_old_prefix
from modules.separation import separate_data
from modules.matching import match_parts

print("Loading sample rows from Excel...")
# Read enough rows to catch both Added and Deleted
df = pd.read_excel('Compare 7th july with 19th JAN.xlsx', skiprows=lambda x: x not in range(0,1) and x < 28000)
print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

structure = detect_structure(df)
prefix    = detect_old_prefix(df)
print(f"\nDetected structure : {structure!r}")
print(f"Detected prefix    : {prefix!r}")

added_df, deleted_df = separate_data(df, structure)
print(f"\nAdded rows  : {len(added_df)}")
print(f"Deleted rows: {len(deleted_df)}")

if len(added_df) > 0:
    # Show a few key columns from added
    show_cols = [c for c in added_df.columns if 'part' in str(c).lower()][:3]
    print("\nSample added PART NO cols:", show_cols)
    print(added_df[show_cols].head(3).to_string())

if len(deleted_df) > 0:
    show_cols = [c for c in deleted_df.columns if 'part' in str(c).lower()][:3]
    print("\nSample deleted PART NO cols:", show_cols)
    print(deleted_df[show_cols].head(3).to_string())

print("\nRunning match_parts...")
try:
    modified, new, removed = match_parts(added_df, deleted_df)
    print(f"\n✅ Results:")
    print(f"  Modified : {len(modified)}")
    print(f"  New      : {len(new)}")
    print(f"  Removed  : {len(removed)}")
    if len(modified) > 0 and 'CHANGES' in modified.columns:
        print("\nSample CHANGES:", modified.iloc[0]['CHANGES'])
except Exception as e:
    print(f"\n❌ match_parts failed: {e}")
    import traceback; traceback.print_exc()
