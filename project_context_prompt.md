# 🔧 Industrial Comparison Analysis System — Full Project Context

You are an expert Python + Streamlit developer continuing implementation of a production-grade comparison analysis system. Below is EVERYTHING you need to know about the project.

---

## 📁 PROJECT LOCATION

```
c:\project\FCS\
```

## 📁 FILE STRUCTURE

```
c:\project\FCS\
├── app.py                          # Streamlit UI (main entry point)
├── .env                            # GROQ_API_KEY (for legacy AI engine)
├── requirements.txt                # pandas, streamlit, xlsxwriter, groq, python-dotenv
├── Compare 7th july with 19th JAN.xlsx   # 33MB sample comparison file (legacy format)
├── modules/
│   ├── ingestion.py                # Excel file reader
│   ├── preprocessing.py            # Structure detection (status, status_dual, schema_based)
│   ├── separation.py               # Split into added/deleted DataFrames
│   ├── matching.py                 # PART NO-based matching (legacy)
│   ├── ai_engine.py                # Groq LLM comment generation (legacy)
│   ├── exporter.py                 # Excel export with formatting
│   ├── transformation.py           # Schema-based row transformer (legacy)
│   └── schema_classifier.py        # Schema-based classifier (legacy)
```

---

## 🎯 APPROVED IMPLEMENTATION PLAN

Redesign the system from **single comparison file** to **two-file upload** (OLD + NEW).

### New Architecture:
1. User uploads TWO Excel files: `old_data.xlsx` and `new_data.xlsx`
2. System auto-analyzes file structure dynamically
3. Compares using **COMPOSITE KEY**: `MODEL YEAR + PART NO + VEH FAM`
4. Classifies rows into **4 categories**: No Change, Modified, New, Deleted
5. Generates **COMMENTS** column (rule-based, NO LLM)
6. Exports formatted Excel with 4 sheets

### New Modules to Create:
- `modules/analysis.py` — File structure analysis & column normalization
- `modules/comparator.py` — Composite key comparison engine
- `modules/comment_engine.py` — Rule-based priority-ordered comments

### Modules to Modify:
- `app.py` — Complete rewrite for two-file flow
- `modules/exporter.py` — 4 sheets, COMMENTS instead of CHANGES

### Modules to Keep (Legacy, no changes):
- `ingestion.py`, `preprocessing.py`, `separation.py`, `matching.py`
- `ai_engine.py`, `transformation.py`, `schema_classifier.py`

---

## 🔷 DETAILED IMPLEMENTATION SPECS

### MODULE 1: `modules/analysis.py` [NEW]

```python
def analyze_file_structure(df):
    """
    Returns dict with:
    - column_names: list of all columns
    - dtypes: dict of column -> dtype
    - sample_rows: first 5 rows as dict
    - key_columns: detected MODEL YEAR, PART NO, VEH FAM columns
    - column_map: original_name -> normalized_name mapping
    """

def normalize_columns(df):
    """
    - Uppercase all column names
    - Strip whitespace
    - Return (cleaned_df, column_map)
    """

def resolve_column(columns, candidates):
    """
    Flexibly resolve a column name from candidates list.
    Example: resolve_column(df.columns, ['MODEL YEAR', 'MODEL_YEAR', 'MODELYEAR'])
    Returns the actual column name found, or None.
    """
```

### MODULE 2: `modules/comparator.py` [NEW]

```python
def build_composite_key(df):
    """
    Creates __KEY__ column = 'MODEL_YEAR|PART_NO|VEH_FAM'
    - Handles missing VEH FAM (fallback to MODEL_YEAR|PART_NO)
    - Normalizes: strip, uppercase, convert NaN safely
    """

def compare_datasets(old_df, new_df):
    """
    Returns (modified_df, new_df, deleted_df, nochange_df)
    
    Logic:
    1. Build composite key on both
    2. Outer merge on __KEY__
    3. key in both + all values same → nochange_df
    4. key in both + at least one value differs → modified_df (with CHANGES dict)
    5. key only in new → new_df
    6. key only in old → deleted_df
    
    Use pandas merge with indicator=True for efficiency.
    """

def detect_changes(old_row, new_row, columns):
    """
    Compare column-by-column.
    Returns changes_dict: {column: "old_value → new_value"}
    NaN-safe comparison (NaN == NaN should be True).
    Returns {} if all values match.
    """
```

### MODULE 3: `modules/comment_engine.py` [NEW]

```python
PRIORITY_FIELDS = [
    "TORQUE STRATEGY",
    "TRGT",
    "TORQUE SNUG TARGET",
    "TRGT2",
    "PART USAGE DESC",
    "PHYSCL DESC",
    "QUANTITY",
    "ENGINE",
    "TRANSMISSION",
    "NOUN DESC"
]

def generate_comment(changes_dict, selected_fields=None):
    """
    Convert changes_dict into single formatted string.
    
    1. Filter: keep only selected_fields (default = PRIORITY_FIELDS)
    2. Order: priority fields first (in PRIORITY_FIELDS order), then remaining
    3. Format: "FIELD: old → new | FIELD: old → new"
    
    Returns empty string if no changes match selected fields.
    """

def generate_comments_batch(df, mode, selected_fields=None):
    """
    Apply comments to entire DataFrame.
    
    mode = "modified" → use generate_comment() on CHANGES column
    mode = "new" → "Completely New Part Added"
    mode = "deleted" → "Part Removed in New Report"
    mode = "nochange" → "No Changes Detected"
    
    Adds COMMENTS column, drops CHANGES column.
    Returns cleaned DataFrame.
    """
```

### MODULE 4: `app.py` [REWRITE]

```
UI Layout:
1. Title: "🔧 Industrial Comparison Analysis System"
2. Sidebar or columns: Two file uploaders (OLD, NEW)
3. Expandable: File structure analysis display
4. MODEL YEAR multiselect filter (populated from data)
5. Field selection multiselect (default = PRIORITY_FIELDS)
   - Preset buttons: "Important Only" / "All Fields"
6. Metrics row: Total Old | Total New | No Change | Modified | New | Deleted
7. Tabs (in order): ⚪ No Change | 🟡 Modified | 🟢 New | 🔴 Deleted
8. Download button for Excel report
```

### MODULE 5: `modules/exporter.py` [MODIFY]

```
Changes:
- export_excel(nochange, modified, new, removed) → 4 DataFrames
- 4 sheets: "No Change" (grey) | "Modified" (amber) | "New" (green) | "Deleted" (red)
- Handle COMMENTS column (not CHANGES)
- Keep existing formatting: header style, alt rows, filters, freeze panes, zoom
```

---

## 🔷 CURRENT SOURCE CODE

### `modules/ingestion.py`
```python
import pandas as pd
def load_file(file):
    return pd.read_excel(file)
```

### `modules/exporter.py`
```python
import pandas as pd
import io
import json


def _format_changes(changes_value):
    """Convert CHANGES dict to a readable multiline string: 'Field: old → new'"""
    if isinstance(changes_value, dict):
        if not changes_value:
            return ""
        lines = []
        for col, diff in changes_value.items():
            lines.append(f"{col}: {diff}")
        return "\n".join(lines)
    if isinstance(changes_value, str):
        try:
            parsed = json.loads(changes_value.replace("'", '"'))
            return _format_changes(parsed)
        except Exception:
            return changes_value
    return str(changes_value) if changes_value else ""


def _sanitize_for_excel(df):
    """Sanitize a dataframe so every cell is Excel-safe."""
    safe_df = df.copy()
    for col in safe_df.columns:
        if str(col).upper() == "CHANGES":
            safe_df[col] = safe_df[col].apply(_format_changes)
        else:
            safe_df[col] = safe_df[col].apply(
                lambda v: json.dumps(v, ensure_ascii=False)
                if isinstance(v, (dict, list, tuple, set))
                else v
            )
    return safe_df


def _col_width(series, col_name, max_width=60, min_width=10):
    """Estimate a sensible column width based on content length."""
    header_len = len(str(col_name))
    try:
        content_len = series.astype(str).str.split("\n").str[0].str.len().max()
    except Exception:
        content_len = header_len
    return min(max(int(content_len or 0), header_len, min_width), max_width)


def _write_sheet(writer, df, sheet_name, tab_color):
    """Write one sheet with full formatting."""
    workbook  = writer.book
    worksheet = workbook.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = worksheet

    header_fmt = workbook.add_format({
        "bold":        True,
        "font_name":   "Calibri",
        "font_size":   11,
        "bg_color":    "#1F497D",
        "font_color":  "#FFFFFF",
        "border":      1,
        "border_color":"#999999",
        "align":       "center",
        "valign":      "vcenter",
        "text_wrap":   False,
    })

    cell_fmt = workbook.add_format({
        "font_name":   "Calibri",
        "font_size":   10,
        "border":      1,
        "border_color":"#D9D9D9",
        "valign":      "top",
        "text_wrap":   False,
    })

    changes_fmt = workbook.add_format({
        "font_name":   "Calibri",
        "font_size":   10,
        "border":      1,
        "border_color":"#D9D9D9",
        "valign":      "top",
        "text_wrap":   True,
        "bg_color":    "#FFF2CC",
    })

    alt_row_fmt = workbook.add_format({
        "font_name":   "Calibri",
        "font_size":   10,
        "border":      1,
        "border_color":"#D9D9D9",
        "valign":      "top",
        "text_wrap":   False,
        "bg_color":    "#F2F2F2",
    })

    worksheet.set_tab_color(tab_color)

    cols = list(df.columns)
    for c_idx, col in enumerate(cols):
        worksheet.write(0, c_idx, str(col), header_fmt)

    for r_idx, row in enumerate(df.itertuples(index=False), start=1):
        row_bg = alt_row_fmt if r_idx % 2 == 0 else cell_fmt
        for c_idx, col in enumerate(cols):
            val = row[c_idx]
            use_fmt = changes_fmt if str(col).upper() == "CHANGES" else row_bg
            if pd.isna(val) if not isinstance(val, str) else False:
                val = ""
            worksheet.write(r_idx, c_idx, val, use_fmt)

    for c_idx, col in enumerate(cols):
        if str(col).upper() == "CHANGES":
            worksheet.set_column(c_idx, c_idx, 55)
        elif str(col).upper() == "COMMENTS":
            worksheet.set_column(c_idx, c_idx, 50)
        else:
            w = _col_width(df[col], col)
            worksheet.set_column(c_idx, c_idx, w)

    worksheet.set_row(0, 22)
    for r_idx in range(1, len(df) + 1):
        worksheet.set_row(r_idx, 18)

    worksheet.freeze_panes(1, 0)

    if len(df):
        worksheet.autofilter(0, 0, len(df), len(cols) - 1)

    worksheet.set_zoom(90)


def export_excel(modified, new, removed):
    output = io.BytesIO()

    safe_modified = _sanitize_for_excel(modified)
    safe_new      = _sanitize_for_excel(new)
    safe_removed  = _sanitize_for_excel(removed)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        _write_sheet(writer, safe_modified, "Modified",  "#FFC000")
        _write_sheet(writer, safe_new,      "New",       "#70AD47")
        _write_sheet(writer, safe_removed,  "Deleted",   "#FF0000")

        writer.book.set_properties({
            "title":   "Industrial Comparison Report",
            "subject": "Part Comparison Analysis",
            "author":  "FCS Analysis System",
        })

    return output.getvalue()
```

### `app.py` (current — will be rewritten)
```python
import streamlit as st
from modules.ingestion import load_file
from modules.preprocessing import detect_structure
from modules.separation import separate_data
from modules.matching import match_parts
from modules.transformation import transform_old_new
from modules.schema_classifier import classify_transformed
from modules.ai_engine import generate_comments
from modules.exporter import export_excel

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align:center;'>🔧 Industrial Comparison Analysis System</h1>", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded:
    df = load_file(uploaded)

    with st.spinner("Processing..."):
        structure = detect_structure(df)
        
        if structure == "schema_based":
            records = transform_old_new(df)
            modified, new, removed = classify_transformed(records)
        else:
            added, deleted = separate_data(df, structure)
            modified, new, removed = match_parts(added, deleted)

        modified = generate_comments(modified, "modified")
        new = generate_comments(new, "new")
        removed = generate_comments(removed, "deleted")

    st.success("Analysis Complete")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(df))
    c2.metric("Modified", len(modified))
    c3.metric("New", len(new))
    c4.metric("Deleted", len(removed))

    show_input = st.toggle("View input file", value=False)
    if show_input:
        st.subheader("📥 Input File Preview")
        st.dataframe(df, width='stretch')

    tab1, tab2, tab3 = st.tabs(["🟡 Modified", "🟢 New", "🔴 Deleted"])

    with tab1:
        st.dataframe(modified, width='stretch')

    with tab2:
        st.dataframe(new, width='stretch')

    with tab3:
        st.dataframe(removed, width='stretch')

    excel = export_excel(modified, new, removed)
    st.download_button("Download Excel", excel, file_name="report.xlsx")
```

---

## 🔷 STRICT DESIGN RULES

1. **NEVER use AI/LLM for logic or classification** — only rule-based Python
2. Matching MUST use composite key: `MODEL YEAR + PART NO + VEH FAM`
3. NEVER rely on full row comparison for matching — use key-based lookup
4. ALWAYS perform column-level difference detection for changes
5. DO NOT hardcode column names — detect dynamically
6. Normalize columns: uppercase, strip whitespace
7. Handle NaN safely (NaN == NaN should be treated as equal)
8. Preserve ALL original columns in output
9. No CHANGES column in final output — only COMMENTS string
10. No Change tab/sheet comes FIRST

## 🔷 PRIORITY FIELDS ORDER (for COMMENTS)

```python
PRIORITY_FIELDS = [
    "TORQUE STRATEGY",
    "TRGT",
    "TORQUE SNUG TARGET",
    "TRGT2",
    "PART USAGE DESC",
    "PHYSCL DESC",
    "QUANTITY",
    "ENGINE",
    "TRANSMISSION",
    "NOUN DESC"
]
```

## 🔷 COMMENT FORMAT

```
FIELD: old → new | FIELD: old → new | FIELD: old → new
```
Priority fields appear first (in order), then remaining fields.

## 🔷 ENVIRONMENT

- Python venv at: `c:\project\FCS\venv\`
- Activate: `& c:\project\FCS\venv\Scripts\Activate.ps1`
- Run with: `c:\project\FCS\venv\Scripts\python`
- Streamlit: `streamlit run app.py`
- OS: Windows
- `.env` contains: `GROQ_API_KEY=...` (legacy, not needed for new flow)

## 🔷 IMPLEMENTATION ORDER

1. Create `modules/analysis.py`
2. Create `modules/comparator.py`
3. Create `modules/comment_engine.py`
4. Modify `modules/exporter.py` (4 sheets, COMMENTS column)
5. Rewrite `app.py` (two-file upload, filters, 4 tabs)
6. Test with synthetic data
7. Test with real Excel files

---

**Start implementation from step 1. Do NOT skip steps. Test each module before moving to the next.**
