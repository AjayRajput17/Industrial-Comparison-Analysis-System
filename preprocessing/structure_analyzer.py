"""
Structure Analyzer — Hybrid Header Detection.

FAST PATH (default):
  Use known EBOM template structure (sheet + header rows) for instant load.

FALLBACK (automatic):
  If fast path fails, fall back to dynamic row-by-row scanning.
"""

import pandas as pd
import io
from config.report_structure_config import (
    DEFAULT_SHEET_NAME,
    DEFAULT_HEADER_ROWS,
    REQUIRED_VALIDATION_COLUMNS,
)


def analyze_multilevel_headers(df: pd.DataFrame):
    """
    Analyzes and prints multi-level header paths for debugging and mapping.
    """
    paths = []
    print("\n--- MULTI-LEVEL HEADER ANALYSIS ---")
    for col in df.columns:
        if isinstance(col, tuple):
            clean_path = tuple(str(c) if not str(c).startswith("Unnamed:") else "---" for c in col)
            print(f"Path -> {clean_path}")
            paths.append(col)
        else:
            print(f"Flat -> {col}")
            paths.append((col,))
    print("----------------------------------\n")
    return paths


def _validate_loaded_structure(df):
    """
    Validate that required business columns exist in the loaded DataFrame.

    Checks leaf-level column names (last element of MultiIndex tuples).

    Returns
    -------
    (is_valid, found_columns, missing_columns)
    """
    # Extract all leaf-level column names (normalized)
    leaf_names = set()
    for col in df.columns:
        if isinstance(col, tuple):
            leaf = " ".join(str(col[-1]).upper().strip().split())
            leaf_names.add(leaf)
        else:
            leaf_names.add(" ".join(str(col).upper().strip().split()))

    found = []
    missing = []
    for req in REQUIRED_VALIDATION_COLUMNS:
        if req.upper() in leaf_names:
            found.append(req)
        else:
            missing.append(req)

    return len(missing) == 0, found, missing


def load_known_template_structure(file_bytes):
    """
    FAST PATH: Load EBOM using known template structure.

    Attempts direct load with:
      sheet_name = "Torque Report"
      header = [0, 1, 2]

    Returns
    -------
    (success, header_idx, df, strategy_info)
        success: bool
        header_idx: int (header row index used)
        df: DataFrame (or None if failed)
        strategy_info: dict with diagnostic metadata
    """
    strategy_info = {"strategy": "fast_path"}

    # Try calamine engine first (Rust-based, ~7x faster), fallback to openpyxl
    engine = "calamine"
    try:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=DEFAULT_SHEET_NAME,
            header=DEFAULT_HEADER_ROWS,
            engine="calamine",
        )
        strategy_info["engine"] = "calamine"
    except Exception:
        try:
            df = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=DEFAULT_SHEET_NAME,
                header=DEFAULT_HEADER_ROWS,
                engine="openpyxl",
            )
            strategy_info["engine"] = "openpyxl"
        except Exception as e:
            strategy_info["fast_path_error"] = str(e)
            return False, 0, None, strategy_info

    strategy_info["sheet_name"] = DEFAULT_SHEET_NAME
    strategy_info["header_rows"] = DEFAULT_HEADER_ROWS

    # Validate the loaded structure
    is_valid, found, missing = _validate_loaded_structure(df)

    strategy_info["validation_found"] = found
    strategy_info["validation_missing"] = missing

    if not is_valid:
        strategy_info["fast_path_error"] = f"Missing required columns: {missing}"
        return False, 0, None, strategy_info

    header_idx = DEFAULT_HEADER_ROWS[-1]  # Last header row index
    strategy_info["rows_loaded"] = len(df)
    strategy_info["columns_loaded"] = len(df.columns)

    return True, header_idx, df, strategy_info


def fallback_dynamic_header_detection(file_bytes, required_keywords=None):
    """
    FALLBACK: Dynamic header detection via row-by-row scanning.
    Only used when fast path fails.

    Returns
    -------
    (header_idx, df, strategy_info)
    """
    strategy_info = {"strategy": "fallback_dynamic"}

    if required_keywords is None:
        required_keywords = ["MODEL YEAR", "PART NO", "VEH FAM"]

    keywords_upper = [str(k).upper().strip() for k in required_keywords]

    # 1. Read first 20 rows raw to find header location
    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, nrows=20)

    target_header_index = 0

    for i in range(len(df_raw)):
        row_values = []
        for val in df_raw.iloc[i].values:
            if pd.notna(val):
                cleaned = " ".join(str(val).upper().strip().split())
                row_values.append(cleaned)

        matches = sum(1 for kw in keywords_upper if kw in row_values)
        if matches == len(keywords_upper):
            target_header_index = i
            break

    # 2. Calculate multi-index header range
    header_start = max(0, target_header_index - 2)
    header_list = list(range(header_start, target_header_index + 1))

    strategy_info["detected_header_index"] = target_header_index
    strategy_info["header_rows"] = header_list

    # 3. Reload with discovered headers
    df_actual = pd.read_excel(io.BytesIO(file_bytes), header=header_list)

    strategy_info["rows_loaded"] = len(df_actual)
    strategy_info["columns_loaded"] = len(df_actual.columns)

    return target_header_index, df_actual, strategy_info


def detect_header_row(file_bytes, required_keywords=None):
    """
    Hybrid header detection: fast path first, fallback if needed.

    Returns
    -------
    (header_idx, df)
        header_idx: int — the detected header row index
        df: DataFrame with MultiIndex columns
    """
    # Try fast path first
    success, header_idx, df, info = load_known_template_structure(file_bytes)

    if success:
        return header_idx, df

    # Fallback to dynamic detection
    header_idx, df, _ = fallback_dynamic_header_detection(file_bytes, required_keywords)
    return header_idx, df


def detect_header_row_with_diagnostics(file_bytes, required_keywords=None):
    """
    Same as detect_header_row but returns full strategy diagnostics.

    Returns
    -------
    (header_idx, df, strategy_info)
    """
    # Try fast path first
    success, header_idx, df, info = load_known_template_structure(file_bytes)

    if success:
        return header_idx, df, info

    # Fallback to dynamic detection
    header_idx, df, fallback_info = fallback_dynamic_header_detection(file_bytes, required_keywords)
    return header_idx, df, fallback_info
