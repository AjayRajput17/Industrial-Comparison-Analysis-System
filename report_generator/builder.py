"""
Report Generator Builder.
Authoritative Pipeline:
  Load MBOM → Header Detection → Normalization → Business Filtering →
  Field Mapping → Type Normalization → Business Deduplication →
  Row ID Generation → Apply Report Schema → Export
"""

import pandas as pd
from preprocessing.structure_analyzer import detect_header_row, analyze_multilevel_headers
from preprocessing.normalizer import normalize_dataframe_columns
from utils.rowid_generator import apply_row_ids
from config.column_mapping import COLUMN_MAPPING
from config.report_schema import REPORT_COLUMNS
from validation.business_filters import apply_all_business_filters
from validation.deduplication_validator import (
    detect_duplicates,
    remove_duplicates,
    validate_rowid_uniqueness,
)


def extract_target_schema(reference_file_bytes: bytes = None) -> list:
    """
    Returns the authoritative target column list.
    Uses config/report_schema.py by default.
    If reference_file_bytes is provided, extracts from that file (optional override).
    """
    if reference_file_bytes is not None:
        import io
        df_ref = pd.read_excel(io.BytesIO(reference_file_bytes), nrows=0)
        from preprocessing.normalizer import normalize_columns
        return normalize_columns(df_ref.columns.tolist())
    return list(REPORT_COLUMNS)


def build_business_report_from_raw(
    raw_file_bytes: bytes,
    reference_file_bytes: bytes = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Executes the strict MBOM-to-report generation flow.
    Pipeline:
      1. Detect target schema (from config or optional override)
      2. Header detection
      3. Normalization
      4. Business filtering (PART STATUS, TORQUE SAFETY, TRGT)
      5. Field mapping (RESIDUAL values)
      6. Type normalization
      7. Business deduplication (subset-based)
      8. Row ID generation
      9. Apply report schema ordering
    """
    diagnostics = {}

    # ── 1. Target Schema ──────────────────────────────────────────────────────
    target_columns = extract_target_schema(reference_file_bytes)
    diagnostics["target_columns_count"] = len(target_columns)
    diagnostics["schema_source"] = "config/report_schema.py" if reference_file_bytes is None else "uploaded reference file"

    # ── 2. Header Detection ───────────────────────────────────────────────────
    header_idx, df_raw = detect_header_row(raw_file_bytes)
    diagnostics["detected_header_row_index"] = header_idx
    diagnostics["rows_after_header_detection"] = len(df_raw)

    # ── 3. Normalization ──────────────────────────────────────────────────────
    raw_paths = analyze_multilevel_headers(df_raw)
    df_raw = normalize_dataframe_columns(df_raw)
    diagnostics["normalized_raw_columns_count"] = len(df_raw.columns)

    # ── 4. Business Filtering (on RAW data, before mapping) ───────────────────
    df_raw, diagnostics = apply_all_business_filters(df_raw, diagnostics)

    # ── 5. Field Mapping ──────────────────────────────────────────────────────
    # Build flat lookup for fallback matching
    flat_lookup = {}
    for col_tuple in df_raw.columns:
        if isinstance(col_tuple, tuple):
            leaf = str(col_tuple[-1])
            if leaf not in flat_lookup:
                flat_lookup[leaf] = col_tuple
        else:
            flat_lookup[str(col_tuple)] = col_tuple

    df_final = pd.DataFrame()
    matched_fields = []
    unmatched_fields = []

    for target_col in target_columns:
        if target_col == "ROW ID":
            continue  # Handled by Row ID Engine

        mapped = False

        # Check explicit MultiIndex tuple rule
        if target_col in COLUMN_MAPPING:
            rule_path = tuple(
                " ".join(str(part).upper().strip().split())
                for part in COLUMN_MAPPING[target_col]
            )
            if rule_path in df_raw.columns:
                df_final[target_col] = df_raw[rule_path].values
                matched_fields.append(f"{target_col} -> {rule_path}")
                mapped = True

        # Fallback to flat leaf match
        if not mapped:
            if target_col in flat_lookup:
                best_tuple = flat_lookup[target_col]
                df_final[target_col] = df_raw[best_tuple].values
                matched_fields.append(f"{target_col} -> {best_tuple} (Flat Fallback)")
                mapped = True

        if not mapped:
            df_final[target_col] = ""
            unmatched_fields.append(target_col)

    diagnostics["matched_fields"] = matched_fields
    diagnostics["unmatched_fields"] = unmatched_fields

    # ── 6. Type Normalization ─────────────────────────────────────────────────
    from preprocessing.type_normalizer import normalize_types
    df_final = normalize_types(df_final)

    # ── 7. Business Deduplication (subset-based, after mapping) ────────────────
    dedupe_diags = detect_duplicates(df_final)
    diagnostics.update(dedupe_diags)

    df_final = remove_duplicates(df_final)

    # ── 8. Row ID Generation ──────────────────────────────────────────────────
    if "ROW ID" in target_columns:
        df_final = apply_row_ids(df_final)

    # ── 9. Apply Report Schema Ordering ───────────────────────────────────────
    final_ordered_columns = [col for col in target_columns if col in df_final.columns]
    df_final = df_final[final_ordered_columns]

    # ── 10. Post-Dedup Validation ─────────────────────────────────────────────
    validation_diags = validate_rowid_uniqueness(df_final)
    diagnostics.update(validation_diags)

    diagnostics["final_report_schema"] = df_final.columns.tolist()
    diagnostics["rows_generated"] = len(df_final)

    return df_final, diagnostics
