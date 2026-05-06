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
        # Already a string – attempt to parse if it looks like a dict repr
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
        col_upper = str(col).upper()
        if col_upper == "CHANGES":
            safe_df[col] = safe_df[col].apply(_format_changes)
        elif col_upper == "COMMENTS":
            # COMMENTS is already a string — just ensure it's clean
            safe_df[col] = safe_df[col].fillna("").astype(str)
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
        if pd.isna(content_len):
            content_len = 0
    except Exception:
        content_len = 0
    return min(max(int(content_len), header_len, min_width), max_width)


def _write_sheet(writer, df, sheet_name, tab_color):
    """Write one sheet with full formatting."""
    workbook  = writer.book
    worksheet = workbook.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = worksheet

    # ── Formats ────────────────────────────────────────────────────────────────
    header_fmt = workbook.add_format({
        "bold":        True,
        "font_name":   "Calibri",
        "font_size":   11,
        "bg_color":    "#1F497D",   # dark navy (matches typical BOM tools)
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
        "text_wrap":   True,           # wrap for multiline changes
        "bg_color":    "#FFF2CC",      # light yellow highlight
    })

    alt_row_fmt = workbook.add_format({
        "font_name":   "Calibri",
        "font_size":   10,
        "border":      1,
        "border_color":"#D9D9D9",
        "valign":      "top",
        "text_wrap":   False,
        "bg_color":    "#F2F2F2",     # subtle alternating row shade
    })

    # ── Tab colour ─────────────────────────────────────────────────────────────
    worksheet.set_tab_color(tab_color)

    # ── Headers ────────────────────────────────────────────────────────────────
    cols = list(df.columns)
    for c_idx, col in enumerate(cols):
        worksheet.write(0, c_idx, str(col), header_fmt)

    # ── Data rows ──────────────────────────────────────────────────────────────
    for r_idx, row in enumerate(df.itertuples(index=False), start=1):
        row_bg = alt_row_fmt if r_idx % 2 == 0 else cell_fmt
        for c_idx, col in enumerate(cols):
            val = row[c_idx]
            col_upper = str(col).upper()
            use_fmt = changes_fmt if col_upper in ("CHANGES", "COMMENTS") else row_bg
            # Normalise value
            if pd.isna(val) if not isinstance(val, str) else False:
                val = ""
            worksheet.write(r_idx, c_idx, val, use_fmt)

    # ── Column widths ──────────────────────────────────────────────────────────
    for c_idx, col in enumerate(cols):
        col_upper = str(col).upper()
        if col_upper in ("CHANGES", "COMMENTS"):
            worksheet.set_column(c_idx, c_idx, 60)     # wider for comments
        else:
            w = _col_width(df[col], col)
            worksheet.set_column(c_idx, c_idx, w)

    # ── Row heights ────────────────────────────────────────────────────────────
    worksheet.set_row(0, 22)   # header row taller
    for r_idx in range(1, len(df) + 1):
        worksheet.set_row(r_idx, 18)

    # ── Freeze pane (header + optional key col) ────────────────────────────────
    worksheet.freeze_panes(1, 0)

    # ── Auto-filter on header row ──────────────────────────────────────────────
    if len(df):
        worksheet.autofilter(0, 0, len(df), len(cols) - 1)

    # ── Sheet zoom ─────────────────────────────────────────────────────────────
    worksheet.set_zoom(90)


def export_excel(nochange, modified, new, removed):
    """Export 4 DataFrames to a formatted Excel workbook with 4 sheets."""
    output = io.BytesIO()

    safe_nochange = _sanitize_for_excel(nochange)
    safe_modified = _sanitize_for_excel(modified)
    safe_new      = _sanitize_for_excel(new)
    safe_removed  = _sanitize_for_excel(removed)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        _write_sheet(writer, safe_nochange, "No Change", "#A6A6A6")   # grey
        _write_sheet(writer, safe_modified, "Modified",  "#FFC000")   # amber
        _write_sheet(writer, safe_new,      "New",       "#70AD47")   # green
        _write_sheet(writer, safe_removed,  "Deleted",   "#FF0000")   # red

        writer.book.set_properties({
            "title":   "Industrial Comparison Report",
            "subject": "Part Comparison Analysis",
            "author":  "FCS Analysis System",
        })

    return output.getvalue()