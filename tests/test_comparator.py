"""
test_comparator.py — Synthetic test for the two-file comparison pipeline.

Tests all 4 categories: No Change, Modified, New, Deleted.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
from preprocessing.analysis import analyze_file_structure, normalize_columns
from comparison_engine.comparator import compare_datasets
from comparison_engine.comment_engine import generate_comments_batch, PRIORITY_FIELDS
from exports.excel_exporter import export_excel


def build_test_data():
    """Build synthetic OLD and NEW DataFrames."""

    old_df = pd.DataFrame([
        # Row 1: will be NO CHANGE (identical in both)
        {"MODEL YEAR": 2024, "PART NO": "AAA-001", "VEH FAM": "WL",
         "QUANTITY": 10, "TRGT": 50, "PART USAGE DESC": "Bolt"},
        # Row 2: will be MODIFIED (QUANTITY changes 5→8, TRGT changes 100→120)
        {"MODEL YEAR": 2024, "PART NO": "BBB-002", "VEH FAM": "WL",
         "QUANTITY": 5, "TRGT": 100, "PART USAGE DESC": "Nut"},
        # Row 3: will be DELETED (only in old)
        {"MODEL YEAR": 2025, "PART NO": "CCC-003", "VEH FAM": "JL",
         "QUANTITY": 20, "TRGT": 200, "PART USAGE DESC": "Washer"},
        # Row 4: will be MODIFIED (PART USAGE DESC changes)
        {"MODEL YEAR": 2025, "PART NO": "DDD-004", "VEH FAM": "JL",
         "QUANTITY": 3, "TRGT": 75, "PART USAGE DESC": "Old Bracket"},
    ])

    new_df = pd.DataFrame([
        # Row 1: NO CHANGE
        {"MODEL YEAR": 2024, "PART NO": "AAA-001", "VEH FAM": "WL",
         "QUANTITY": 10, "TRGT": 50, "PART USAGE DESC": "Bolt"},
        # Row 2: MODIFIED
        {"MODEL YEAR": 2024, "PART NO": "BBB-002", "VEH FAM": "WL",
         "QUANTITY": 8, "TRGT": 120, "PART USAGE DESC": "Nut"},
        # Row 3 (CCC-003) is MISSING → DELETED
        # Row 4: MODIFIED
        {"MODEL YEAR": 2025, "PART NO": "DDD-004", "VEH FAM": "JL",
         "QUANTITY": 3, "TRGT": 75, "PART USAGE DESC": "New Bracket"},
        # Row 5: NEW (only in new)
        {"MODEL YEAR": 2025, "PART NO": "EEE-005", "VEH FAM": "JL",
         "QUANTITY": 15, "TRGT": 60, "PART USAGE DESC": "Clip"},
    ])

    return old_df, new_df


def test_analysis():
    """Test file structure analysis."""
    old_df, new_df = build_test_data()

    old_info = analyze_file_structure(old_df)
    assert old_info["row_count"] == 4
    assert "MODEL YEAR" in old_info["key_columns"]
    assert "PART NO" in old_info["key_columns"]
    assert "VEH FAM" in old_info["key_columns"]
    assert len(old_info["missing_keys"]) == 0
    print("✅ analysis: structure detection OK")


def test_comparison():
    """Test core comparison logic."""
    old_df, new_df = build_test_data()

    modified, new_only, deleted, nochange = compare_datasets(old_df, new_df)

    # No Change: AAA-001
    assert len(nochange) == 1, f"Expected 1 no-change, got {len(nochange)}"
    print(f"✅ No Change: {len(nochange)} (AAA-001)")

    # Modified: BBB-002, DDD-004
    assert len(modified) == 2, f"Expected 2 modified, got {len(modified)}"
    assert "CHANGES" in modified.columns
    print(f"✅ Modified: {len(modified)} (BBB-002, DDD-004)")

    # New: EEE-005
    assert len(new_only) == 1, f"Expected 1 new, got {len(new_only)}"
    print(f"✅ New: {len(new_only)} (EEE-005)")

    # Deleted: CCC-003
    assert len(deleted) == 1, f"Expected 1 deleted, got {len(deleted)}"
    print(f"✅ Deleted: {len(deleted)} (CCC-003)")

    # Check CHANGES content for BBB-002
    bbb_changes = None
    for _, row in modified.iterrows():
        if "BBB-002" in str(row.get("PART NO", "")):
            bbb_changes = row["CHANGES"]
            break
    assert bbb_changes is not None, "BBB-002 not found in modified"
    assert "QUANTITY" in bbb_changes, f"QUANTITY not in changes: {bbb_changes}"
    assert "TRGT" in bbb_changes, f"TRGT not in changes: {bbb_changes}"
    print(f"✅ CHANGES for BBB-002: {bbb_changes}")


def test_comments():
    """Test comment generation."""
    old_df, new_df = build_test_data()
    modified, new_only, deleted, nochange = compare_datasets(old_df, new_df)

    mod_out  = generate_comments_batch(modified, "modified", PRIORITY_FIELDS)
    new_out  = generate_comments_batch(new_only, "new")
    del_out  = generate_comments_batch(deleted,  "deleted")
    nc_out   = generate_comments_batch(nochange, "nochange")

    assert "COMMENTS" in mod_out.columns
    assert "CHANGES" not in mod_out.columns   # must be dropped
    assert "COMMENTS" in new_out.columns
    assert "COMMENTS" in del_out.columns
    assert "COMMENTS" in nc_out.columns

    # Check format: should contain "|" separator for multi-field changes
    bbb_comment = mod_out[mod_out["COMMENTS"].str.contains("TRGT")].iloc[0]["COMMENTS"]
    assert "\n" in bbb_comment, f"Expected newline in comment: {bbb_comment}"
    print(f"✅ Comment for BBB-002: {bbb_comment}")
    print(f"✅ New comment: {new_out.iloc[0]['COMMENTS']}")
    print(f"✅ Deleted comment: {del_out.iloc[0]['COMMENTS']}")
    print(f"✅ No Change comment: {nc_out.iloc[0]['COMMENTS']}")


def test_export():
    """Test Excel export with 4 sheets."""
    old_df, new_df = build_test_data()
    modified, new_only, deleted, nochange = compare_datasets(old_df, new_df)

    nc_out  = generate_comments_batch(nochange, "nochange")
    mod_out = generate_comments_batch(modified, "modified", PRIORITY_FIELDS)
    new_out = generate_comments_batch(new_only, "new")
    del_out = generate_comments_batch(deleted,  "deleted")

    data = export_excel(nc_out, mod_out, new_out, del_out)
    assert len(data) > 0, "Export produced empty bytes"

    # Verify 4 sheets
    from io import BytesIO
    sheets = pd.ExcelFile(BytesIO(data)).sheet_names
    assert sheets == ["No Change", "Modified", "New", "Deleted"], f"Sheets: {sheets}"
    print(f"✅ Export OK: {len(data):,} bytes, sheets: {sheets}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Two-File Comparison Pipeline")
    print("=" * 60)

    test_analysis()
    test_comparison()
    test_comments()
    test_export()

    print()
    print("=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)
