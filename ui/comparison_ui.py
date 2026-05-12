import streamlit as st
import pandas as pd
from utils.ingestion import load_file
from preprocessing.analysis import analyze_file_structure, normalize_columns
from comparison_engine.comparator import compare_datasets
from comparison_engine.comment_engine import (
    PRIORITY_FIELDS,
    generate_comments_batch,
)
from exports.exporter import export_excel

def render():
    st.markdown(
        "<h1 style='text-align:center;'>🔧 Industrial Comparison Analysis System</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#888;'>"
        "Upload OLD and NEW reports to compare parts across model years."
        "</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── File uploaders ─────────────────────────────────────────────────────────────
    col_old, col_new = st.columns(2)

    with col_old:
        st.subheader("📂 OLD Report")
        old_file = st.file_uploader(
            "Upload the OLD Excel file", type=["xlsx"], key="old_file"
        )

    with col_new:
        st.subheader("📂 NEW Report")
        new_file = st.file_uploader(
            "Upload the NEW Excel file", type=["xlsx"], key="new_file"
        )

    # ── Guard: need both files ────────────────────────────────────────────────────
    if not old_file or not new_file:
        st.info("⬆️ Please upload both OLD and NEW Excel files to begin analysis.")
        return


    # ── Cached heavy functions ────────────────────────────────────────────────────
    @st.cache_data(show_spinner="Comparing datasets… (this only runs once per file pair)")
    def _cached_compare(old_bytes, old_name, new_bytes, new_name):
        """Cache the entire comparison pipeline by file content."""
        import io
        old_df = pd.read_excel(io.BytesIO(old_bytes))
        new_df = pd.read_excel(io.BytesIO(new_bytes))
        modified, new_only, deleted, nochange = compare_datasets(old_df, new_df)
        return old_df, new_df, modified, new_only, deleted, nochange


    # ── Load & compare (cached) ───────────────────────────────────────────────────
    old_bytes = old_file.getvalue()
    new_bytes = new_file.getvalue()

    old_df, new_df, modified, new_only, deleted, nochange = _cached_compare(
        old_bytes, old_file.name, new_bytes, new_file.name
    )

    # ── File structure analysis (expandable) ───────────────────────────────────────
    with st.expander("🔍 File Structure Analysis", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**OLD file**")
            old_info = analyze_file_structure(old_df)
            st.write(f"Rows: **{old_info['row_count']}** | Columns: **{len(old_info['column_names'])}**")
            st.write("Key columns detected:", old_info["key_columns"])
            if old_info["missing_keys"]:
                st.warning(f"Missing key columns: {old_info['missing_keys']}")
        with c2:
            st.markdown("**NEW file**")
            new_info = analyze_file_structure(new_df)
            st.write(f"Rows: **{new_info['row_count']}** | Columns: **{len(new_info['column_names'])}**")
            st.write("Key columns detected:", new_info["key_columns"])
            if new_info["missing_keys"]:
                st.warning(f"Missing key columns: {new_info['missing_keys']}")


    # ══════════════════════════════════════════════════════════════════════════════
    # FILTERS — Horizontal layout below input preview
    # ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🎛️ Filters")

    # MODEL YEAR filter
    all_years = set()
    for frame in (nochange, modified, new_only, deleted):
        if not frame.empty:
            norm_frame, _ = normalize_columns(frame)
            for candidate in ["MODEL YEAR", "MODEL_YEAR", "MODELYEAR", "MY"]:
                if candidate in norm_frame.columns:
                    all_years.update(
                        norm_frame[candidate].dropna().astype(str).str.strip().unique()
                    )
                    break

    all_years = sorted(all_years)

    selected_years = st.multiselect(
        "📅 Filter by MODEL YEAR",
        options=all_years,
        default=all_years,
    )

    # Row 2: Comment field selection + presets
    st.markdown("**📝 Comment Fields** — select which fields appear in the COMMENTS column")

    # Get all non-key column names
    all_data_cols = set()
    for frame in (modified, new_only, deleted, nochange):
        if not frame.empty:
            all_data_cols.update(c for c in frame.columns if c != "CHANGES")
    all_data_cols = sorted(all_data_cols)

    # Presets + multiselect in one row
    preset_col, field_col = st.columns([1, 3])

    with preset_col:
        st.markdown("")  # spacer
        if st.button("⚡ Important Only"):
            st.session_state["selected_fields"] = [
                f for f in PRIORITY_FIELDS if f in all_data_cols
            ]
        if st.button("📋 All Fields"):
            st.session_state["selected_fields"] = list(all_data_cols)

    default_fields = st.session_state.get(
        "selected_fields",
        [f for f in PRIORITY_FIELDS if f in all_data_cols],
    )

    with field_col:
        selected_fields = st.multiselect(
            "Select fields to display in comments",
            options=all_data_cols,
            default=default_fields,
            label_visibility="collapsed",
        )


    # ══════════════════════════════════════════════════════════════════════════════
    # APPLY FILTERS
    # ══════════════════════════════════════════════════════════════════════════════

    def _filter_by_year(df, years):
        """Filter DataFrame by MODEL YEAR."""
        if df.empty or not years:
            return df
        norm_df, _ = normalize_columns(df)
        for candidate in ["MODEL YEAR", "MODEL_YEAR", "MODELYEAR", "MY"]:
            if candidate in norm_df.columns:
                mask = norm_df[candidate].astype(str).str.strip().isin(years)
                return df[mask.values].reset_index(drop=True)
        return df



    # Apply MODEL YEAR filter
    nochange_f = _filter_by_year(nochange, selected_years)
    modified_f = _filter_by_year(modified, selected_years)
    new_only_f = _filter_by_year(new_only, selected_years)
    deleted_f  = _filter_by_year(deleted,  selected_years)

    # (ROW ID search does NOT filter the tabs — it's a separate lookup below)

    # ── Generate comments ──────────────────────────────────────────────────────────
    nochange_out = generate_comments_batch(nochange_f, "nochange", selected_fields)
    modified_out = generate_comments_batch(modified_f, "modified", selected_fields)
    new_out      = generate_comments_batch(new_only_f, "new",      selected_fields)
    deleted_out  = generate_comments_batch(deleted_f,  "deleted",  selected_fields)




    # ══════════════════════════════════════════════════════════════════════════════
    # METRICS
    # ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Old Rows",     len(old_df))
    m2.metric("New Rows",     len(new_df))
    m3.metric("⚪ No Change", len(nochange_out))
    m4.metric("🟡 Modified",  len(modified_out))
    m5.metric("🟢 New",       len(new_out))
    m6.metric("🔴 Deleted",   len(deleted_out))


    # ══════════════════════════════════════════════════════════════════════════════
    # RESULT TABS
    # ══════════════════════════════════════════════════════════════════════════════
    tab_nc, tab_mod, tab_new, tab_del = st.tabs([
        f"⚪ No Change ({len(nochange_out)})",
        f"🟡 Modified ({len(modified_out)})",
        f"🟢 New ({len(new_out)})",
        f"🔴 Deleted ({len(deleted_out)})",
    ])


    def _display_tab(tab, df, tab_name):
        """Display a result tab with optional comment field filter."""
        with tab:
            if df.empty:
                st.info(f"No {tab_name} parts found.")
                return

            # Comment field filter (for Modified tab — allows filtering by specific field in COMMENTS)
            if tab_name == "modified" and "COMMENTS" in df.columns:
                comment_filter = st.text_input(
                    "🔎 Filter comments (e.g. type 'TORQ' to find torque changes)",
                    value="",
                    key=f"comment_filter_{tab_name}",
                    placeholder="Type to filter within COMMENTS column…",
                )
                if comment_filter.strip():
                    mask = df["COMMENTS"].astype(str).str.upper().str.contains(
                        comment_filter.strip().upper(), na=False
                    )
                    df = df[mask].reset_index(drop=True)
                    st.caption(f"Showing {len(df)} rows matching '{comment_filter}'")

            st.dataframe(df, width="stretch")


    _display_tab(tab_nc,  nochange_out, "no change")
    _display_tab(tab_mod, modified_out, "modified")
    _display_tab(tab_new, new_out,      "new")
    _display_tab(tab_del, deleted_out,  "deleted")


    # ══════════════════════════════════════════════════════════════════════════════
    # ROW ID SEARCH — Below output tabs
    # ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🔍 Search by ROW ID")
    search_row_id = st.text_input(
        "Enter ROW ID",
        value="",
        placeholder="Type a ROW ID to view its full details…",
        label_visibility="collapsed",
    )
