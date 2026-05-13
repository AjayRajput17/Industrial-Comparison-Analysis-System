"""
Report Generator Builder.
Authoritative Pipeline with Performance Timing:
  Load MBOM → Header Detection → Normalization → Business Filtering →
  Field Mapping → Type Normalization → Category Optimization →
  Business Deduplication → Row ID Generation → Apply Report Schema → Export

PERFORMANCE OPTIMIZATIONS:
  - Single normalization pass (no re-normalization)
  - Category dtypes for low-cardinality string columns
  - Vectorized Row ID generation
  - Precomputed filter masks (single slice)
  - Reduced unnecessary DataFrame copies
  - Full step-by-step timing instrumentation
"""

import pandas as pd
from preprocessing.structure_analyzer import (
    detect_header_row_with_diagnostics,
    analyze_multilevel_headers,
)
from preprocessing.normalizer import normalize_dataframe_columns
from utils.rowid_generator import apply_row_ids
from utils.performance_timer import PipelineTimer
from config.column_mapping import COLUMN_MAPPING
from config.report_schema import REPORT_COLUMNS
from validation.business_filters import apply_all_business_filters
from validation.deduplication_validator import (
    detect_duplicates,
    remove_duplicates,
    validate_rowid_uniqueness,
)

# Low-cardinality columns to convert to category dtype after mapping
_CATEGORY_COLUMNS = [
    "VEH FAM", "VEH LINE", "ENGINE", "TRANSMISSION",
    "TORQUE STRATEGY", "TIGHTENING CLASS", "CONDITION DESC",
    "TORQUE SAFETY", "BODY STYLE", "DEPT_REL",
]


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


def _apply_category_dtypes(df):
    """Convert low-cardinality string columns to category dtype for memory + speed."""
    for col in _CATEGORY_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df


def build_business_report_from_raw(
    raw_file_bytes: bytes,
    reference_file_bytes: bytes = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Executes the strict MBOM-to-report generation flow with timing.
    Pipeline:
      1. Detect target schema (from config or optional override)
      2. Header detection (fast-path or fallback)
      3. Normalization
      4. Business filtering (PART STATUS, TORQUE SAFETY, TRGT)
      5. Field mapping (RESIDUAL values)
      6. Type normalization
      7. Business deduplication (subset-based)
      8. Row ID generation (vectorized)
      9. Category dtype optimization
     10. Apply report schema ordering
    """
    timer = PipelineTimer()
    diagnostics = {}

    # ── 1. Target Schema ──────────────────────────────────────────────────────
    timer.start("Schema Resolution")
    target_columns = extract_target_schema(reference_file_bytes)
    diagnostics["target_columns_count"] = len(target_columns)
    diagnostics["schema_source"] = "config/report_schema.py" if reference_file_bytes is None else "uploaded reference file"
    timer.stop("Schema Resolution")

    # ── 2. Header Detection (hybrid: fast-path → fallback) ────────────────────
    timer.start("Header Detection")
    header_idx, df_raw, header_strategy = detect_header_row_with_diagnostics(raw_file_bytes)
    diagnostics["detected_header_row_index"] = header_idx
    diagnostics["rows_after_header_detection"] = len(df_raw)
    diagnostics["header_strategy"] = header_strategy
    timer.stop("Header Detection")

    # ── 3. Normalization (done ONCE, reused everywhere) ───────────────────────
    timer.start("Normalization")
    raw_paths = analyze_multilevel_headers(df_raw)
    df_raw = normalize_dataframe_columns(df_raw)
    diagnostics["normalized_raw_columns_count"] = len(df_raw.columns)
    timer.stop("Normalization")

    # ── 4. Business Filtering (precomputed combined mask, single slice) ───────
    timer.start("Business Filtering")
    df_raw, diagnostics = apply_all_business_filters(df_raw, diagnostics)
    timer.stop("Business Filtering")

    # ── 5. Field Mapping ──────────────────────────────────────────────────────
    timer.start("Field Mapping")
    # Build flat lookup for fallback matching (done once)
    flat_lookup = {}
    for col_tuple in df_raw.columns:
        if isinstance(col_tuple, tuple):
            leaf = str(col_tuple[-1])
            if leaf not in flat_lookup:
                flat_lookup[leaf] = col_tuple
        else:
            flat_lookup[str(col_tuple)] = col_tuple

    # Pre-allocate dict of arrays instead of column-by-column DataFrame assignment
    mapped_data = {}
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
                mapped_data[target_col] = df_raw[rule_path].values
                matched_fields.append(f"{target_col} -> {rule_path}")
                mapped = True

        # Fallback to flat leaf match
        if not mapped:
            if target_col in flat_lookup:
                best_tuple = flat_lookup[target_col]
                mapped_data[target_col] = df_raw[best_tuple].values
                matched_fields.append(f"{target_col} -> {best_tuple} (Flat Fallback)")
                mapped = True

        if not mapped:
            mapped_data[target_col] = ""
            unmatched_fields.append(target_col)

    # Build DataFrame from dict once (faster than repeated column assignment)
    df_final = pd.DataFrame(mapped_data)

    diagnostics["matched_fields"] = matched_fields
    diagnostics["unmatched_fields"] = unmatched_fields
    timer.stop("Field Mapping")

    # ── 6. Type Normalization ─────────────────────────────────────────────────
    timer.start("Type Normalization")
    from preprocessing.type_normalizer import normalize_types
    df_final = normalize_types(df_final)
    timer.stop("Type Normalization")

    # ── 7. Business Deduplication (subset-based, after mapping) ────────────────
    timer.start("Deduplication")
    dedupe_diags = detect_duplicates(df_final)
    diagnostics.update(dedupe_diags)
    df_final = remove_duplicates(df_final)
    timer.stop("Deduplication")

    # ── 8. Row ID Generation (vectorized — must run BEFORE category conversion)
    timer.start("Row ID Generation")
    if "ROW ID" in target_columns:
        df_final = apply_row_ids(df_final)
    timer.stop("Row ID Generation")

    # ── 9. Category Dtype Optimization (after Row ID, before schema ordering) ─
    timer.start("Category Optimization")
    df_final = _apply_category_dtypes(df_final)
    timer.stop("Category Optimization")

    # ── 10. Apply Report Schema Ordering ──────────────────────────────────────
    timer.start("Schema Ordering")
    final_ordered_columns = [col for col in target_columns if col in df_final.columns]
    df_final = df_final[final_ordered_columns]
    timer.stop("Schema Ordering")

    # ── 11. Post-Dedup Validation ─────────────────────────────────────────────
    timer.start("Validation")
    validation_diags = validate_rowid_uniqueness(df_final)
    diagnostics.update(validation_diags)
    timer.stop("Validation")

    diagnostics["final_report_schema"] = df_final.columns.tolist()
    diagnostics["rows_generated"] = len(df_final)

    # Attach timing summary
    diagnostics["timing"] = timer.summary_dict()

    return df_final, diagnostics
