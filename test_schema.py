import sys
import os

# Ensure modules can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
from modules.preprocessing import detect_structure
from modules.transformation import transform_old_new
from modules.schema_classifier import classify_transformed

def test_pipeline():
    # Mock data for Format B
    data = {
        "old_data.part no": ["1001", "1002", None, "1004"],
        "new_data.part no": ["1001", None, "1003", "1004"],
        "old_data.quantity": [10, 5, None, 20],
        "new_data.quantity": [15, None, 8, 20],  # 1001 is modified, 1002 is deleted, 1003 is new, 1004 no changes
    }
    df = pd.DataFrame(data)
    
    structure = detect_structure(df)
    assert structure == "schema_based", f"Expected schema_based, got {structure}"
    
    records = transform_old_new(df)
    assert len(records) == 4
    
    modified, new, removed = classify_transformed(records)
    
    print("Modified parts:")
    print(modified)
    print("\nNew parts:")
    print(new)
    print("\nRemoved parts:")
    print(removed)
    
    # 1001 modified
    assert len(modified) == 1, f"Expected 1 modified, got {len(modified)}"
    assert modified.iloc[0]['part no'] == "1001"
    
    # 1003 new
    assert len(new) == 1
    assert "1003" in new['part no'].values
    
    # 1002 deleted
    assert len(removed) == 1
    assert "1002" in removed['part no'].values

if __name__ == "__main__":
    test_pipeline()
    print("ALL TESTS PASSED")
