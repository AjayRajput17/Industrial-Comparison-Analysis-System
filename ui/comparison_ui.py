import streamlit as st
import pandas as pd
from utils.ingestion import load_file
from preprocessing.analysis import analyze_file_structure, normalize_columns
from comparison_engine.comparator import compare_datasets
from comparison_engine.comment_engine import (
    PRIORITY_FIELDS,
    generate_comments_batch,
)
from exports.comparison_export.comparison_exporter import export_comparison_excel
from exports.comparison_export.comparison_filename import generate_comparison_filename

# Maximum rows to render in preview (full data always available in export)
_PREVIEW_LIMIT = 500


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

    # ── Cached comparison — runs ONCE per file pair ───────────────────────────────
    @st.cache_data(show_spinner="Running 9-column business identity comparison...")
    def _cached_compare(old_bytes, old_name, new_bytes, new_name):
        import io
        old_df = pd.read_excel(io.BytesIO(old_bytes))
        new_df = pd.read_excel(io.BytesIO(new_bytes))
        modified, new_only, deleted, nochange, comp_diags = compare_datasets(old_df, new_df)
        return old_df, new_df, modified, new_only, deleted, nochange, comp_diags

    old_bytes = old_file.getvalue()
    new_bytes = new_file.getvalue()

    old_df, new_df, modified, new_only, deleted, nochange, comp_diags = _cached_compare(
        old_bytes, old_file.name, new_bytes, new_file.name
    )

    # ══════════════════════════════════════════════════════════════════════════════
    # FILE STRUCTURE ANALYSIS (collapsed)
    # ══════════════════════════════════════════════════════════════════════════════
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
    # COMPARISON DIAGNOSTICS (collapsed — lightweight summary only)
    # ══════════════════════════════════════════════════════════════════════════════
    with st.expander("🔬 Comparison Engine Diagnostics", expanded=False):
        st.markdown("#### 🆔 Business Identity Key")

        old_id = comp_diags.get("old_identity", {})
        new_id = comp_diags.get("new_identity", {})

        c_old_d, c_new_d = st.columns(2)
        with c_old_d:
            st.markdown("**OLD File Identity**")
            st.write(f"- Resolved: `{list(old_id.get('resolved_identity_columns', {}).keys())}`")
            if old_id.get("missing_identity_columns"):
                st.warning(f"Missing: {old_id['missing_identity_columns']}")
            st.write(f"- Rows: **{old_id.get('total_rows_after_key_build', 'N/A')}**")
            st.write(f"- Duplicate keys: **{old_id.get('duplicate_identity_count', 0)}**")

        with c_new_d:
            st.markdown("**NEW File Identity**")
            st.write(f"- Resolved: `{list(new_id.get('resolved_identity_columns', {}).keys())}`")
            if new_id.get("missing_identity_columns"):
                st.warning(f"Missing: {new_id['missing_identity_columns']}")
            st.write(f"- Rows: **{new_id.get('total_rows_after_key_build', 'N/A')}**")
            st.write(f"- Duplicate keys: **{new_id.get('duplicate_identity_count', 0)}**")

        st.divider()
        st.markdown("#### 🔗 Matching Results")
        st.write(f"- Common keys: **{comp_diags.get('common_key_count')}**")
        st.write(f"- New-only keys: **{comp_diags.get('new_only_key_count')}**")
        st.write(f"- Deleted keys: **{comp_diags.get('deleted_key_count')}**")

        # ── Rescue Pass Diagnostics ───────────────────────────────────────────
        rescue = comp_diags.get("rescue", {})
        if rescue:
            st.divider()
            st.markdown("#### 🛟 Rescue Pass")
            rescued = rescue.get("rescued_count", 0)
            if rescued > 0:
                st.success(f"✅ Rescued **{rescued}** false Added/Deleted pairs → Modified")
                st.write(f"  - Phase A (ENGINE same): **{rescue.get('phase_a_rescued', 0)}**")
                st.write(f"  - Phase B (ENGINE different, validated): **{rescue.get('phase_b_rescued', 0)}**")
            else:
                st.info("ℹ️ No false Added/Deleted pairs found to rescue")
            st.write(f"  - Remaining true Added: **{rescue.get('remaining_added', 0)}**")
            st.write(f"  - Remaining true Deleted: **{rescue.get('remaining_deleted', 0)}**")

        # ── Duplicate Group Rescue Diagnostics ────────────────────────────────
        dgr = comp_diags.get("duplicate_group_rescue", {})
        if dgr and dgr.get("status") == "COMPLETED":
            st.divider()
            st.markdown("#### 🔄 Duplicate Group Rescue")
            groups_rescued = dgr.get("groups_rescued", 0)
            if groups_rescued > 0:
                m2nc = dgr.get("modified_to_nochange", 0)
                m2dm = dgr.get("modified_to_diff_modified", 0)
                st.success(f"✅ Rescued **{groups_rescued}** duplicate groups with better matches")
                st.write(f"  - Modified → No Change: **{m2nc}**")
                st.write(f"  - Modified → Better Modified: **{m2dm}**")
            else:
                st.info("ℹ️ No duplicate group rescues needed")
            st.write(f"  - Groups analysed: **{dgr.get('duplicate_groups_found', 0)}**")
            st.write(f"  - Rows analysed: **{dgr.get('rows_analysed', 0)}**")

    # ══════════════════════════════════════════════════════════════════════════════
    # ACTIONABILITY SUMMARY
    # ══════════════════════════════════════════════════════════════════════════════
    action_diags = comp_diags.get("actionability", {})
    if action_diags and action_diags.get("status") != "DISABLED via ENABLE_ACTIONABILITY_CLASSIFIER=False":
        with st.expander("🎯 Actionability Summary", expanded=False):
            mod_act = action_diags.get("modified", {})
            add_act = action_diags.get("added", {})

            # ── High-level metrics ────────────────────────────────────────────
            st.markdown("#### Modified Rows")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Modified", mod_act.get("modified_input", 0))
            c2.metric("⚡ Action Required", mod_act.get("action_yes", 0))
            c3.metric("ℹ️ Informational", mod_act.get("action_no", 0))

            st.markdown("#### Added Rows")
            added_yes = add_act.get("added_action_yes", 0)
            added_no = add_act.get("added_action_no", 0)
            if added_no > 0:
                ca1, ca2, ca3 = st.columns(3)
                ca1.metric("Total Added", added_yes + added_no)
                ca2.metric("⚡ Action Required", added_yes)
                ca3.metric("ℹ️ Low Torque (No Action)", added_no)
            else:
                st.write(f"- All **{added_yes}** Added rows → **ACTION REQUIRED = YES**")

            # ── Category breakdown ────────────────────────────────────────────
            st.divider()
            st.markdown("#### 📊 Review Category Breakdown")
            mod_cats = mod_act.get("category_breakdown", {})
            add_cats = add_act.get("category_breakdown", {})
            # Merge both category dicts
            all_cats = {}
            for cat, count in mod_cats.items():
                all_cats[cat] = all_cats.get(cat, 0) + count
            for cat, count in add_cats.items():
                all_cats[cat] = all_cats.get(cat, 0) + count
            if all_cats:
                cat_rows = [{"Review Category": cat, "Count": count}
                            for cat, count in sorted(all_cats.items(), key=lambda x: -x[1])]
                st.table(pd.DataFrame(cat_rows))

            # ── Low torque metrics ────────────────────────────────────────────
            low_t = mod_act.get("low_torque_changes", 0)
            cross = mod_act.get("threshold_crossings", 0)
            admin = mod_act.get("admin_changes", 0)
            if low_t or cross or admin:
                st.divider()
                st.markdown("#### 🔬 Detail Metrics")
                dm1, dm2, dm3 = st.columns(3)
                dm1.metric("Low Torque Changes", low_t)
                dm2.metric("Threshold Crossings", cross)
                dm3.metric("Administrative Only", admin)

    # ══════════════════════════════════════════════════════════════════════════════
    # PERFORMANCE TIMING SUMMARY (collapsed)
    # ══════════════════════════════════════════════════════════════════════════════
    timing = comp_diags.get("timing", {})
    if timing:
        with st.expander("⏱️ Performance Timing Summary", expanded=False):
            total = timing.pop("TOTAL", 0)
            timing_rows = []
            for step, dur in timing.items():
                timing_rows.append({"Stage": step, "Duration (sec)": dur})
            timing_rows.append({"Stage": "**TOTAL**", "Duration (sec)": total})
            st.table(pd.DataFrame(timing_rows))
            timing["TOTAL"] = total

    # ══════════════════════════════════════════════════════════════════════════════
    # SMART RE-MATCH SIMULATOR (Debug Only)
    # ══════════════════════════════════════════════════════════════════════════════
    sm_diags = comp_diags.get("smart_rematch", {})
    if sm_diags and sm_diags.get("diagnostics", {}).get("status") == "COMPLETED":
        with st.expander("🧪 Smart Re-Match Simulator (Debug)", expanded=False):
            st.warning("This is an analytical simulation. These results do not affect the main comparison output.")
            sm_metrics = sm_diags["diagnostics"]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Duplicate Groups", sm_metrics.get("duplicate_groups", 0))
            c2.metric("Rows Analysed", sm_metrics.get("rows_analysed", 0))
            c3.metric("Better Matches Found", sm_metrics.get("potential_better_match", 0))
            
            st.write(f"- **No Impact (Current = Best):** {sm_metrics.get('no_impact', 0)}")
            st.write(f"- **Modified → No Change:** {sm_metrics.get('modified_to_nochange', 0)}")
            st.write(f"- **Modified → Different Modified:** {sm_metrics.get('modified_to_different_modified', 0)}")
            
            if sm_diags.get("excel_bytes"):
                st.download_button(
                    label="Download Smart Re-Match Analysis 📊",
                    data=sm_diags["excel_bytes"],
                    file_name="SMART_REMATCH_ANALYSIS.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    # ══════════════════════════════════════════════════════════════════════════════
    # FILTERS (lightweight — no dataframe rendering here)
    # ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🎛️ Filters")

    # MODEL YEAR filter — extract from lightweight sets
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

    # Comment field selection
    st.markdown("**📝 Comment Fields** — select which fields appear in the COMMENTS column")

    all_data_cols = set()
    for frame in (modified, new_only, deleted, nochange):
        if not frame.empty:
            all_data_cols.update(c for c in frame.columns if c != "CHANGES")
    all_data_cols = sorted(all_data_cols)

    preset_col, field_col = st.columns([1, 3])

    with preset_col:
        st.markdown("")
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
    # APPLY FILTERS + GENERATE COMMENTS (deferred — cached)
    # ══════════════════════════════════════════════════════════════════════════════

    def _filter_by_year(df, years):
        if df.empty or not years:
            return df
        norm_df, _ = normalize_columns(df)
        for candidate in ["MODEL YEAR", "MODEL_YEAR", "MODELYEAR", "MY"]:
            if candidate in norm_df.columns:
                mask = norm_df[candidate].astype(str).str.strip().isin(years)
                return df[mask.values].reset_index(drop=True)
        return df

    nochange_f = _filter_by_year(nochange, selected_years)
    modified_f = _filter_by_year(modified, selected_years)
    new_only_f = _filter_by_year(new_only, selected_years)
    deleted_f  = _filter_by_year(deleted,  selected_years)

    nochange_out = generate_comments_batch(nochange_f, "nochange", selected_fields)
    modified_out = generate_comments_batch(modified_f, "modified", selected_fields)
    new_out      = generate_comments_batch(new_only_f, "new",      selected_fields)
    deleted_out  = generate_comments_batch(deleted_f,  "deleted",  selected_fields)

    # ══════════════════════════════════════════════════════════════════════════════
    # SUMMARY-FIRST METRICS (renders immediately — no heavy DataFrames)
    # ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("📊 Comparison Summary")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Old Rows",     len(old_df))
    m2.metric("New Rows",     len(new_df))
    m3.metric("⚪ No Change", len(nochange_out))
    m4.metric("🟡 Modified",  len(modified_out))
    m5.metric("🟢 New",       len(new_out))
    m6.metric("🔴 Deleted",   len(deleted_out))

    # ══════════════════════════════════════════════════════════════════════════════
    # LAZY DATA PREVIEW — only renders when user clicks a tab
    # ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("📋 Data Preview")
    st.caption(f"Previews show up to {_PREVIEW_LIMIT} rows. Full data is always available in the Excel export.")

    tab_mod, tab_new, tab_del, tab_nc = st.tabs([
        f"🟡 Modified ({len(modified_out)})",
        f"🟢 New ({len(new_out)})",
        f"🔴 Deleted ({len(deleted_out)})",
        f"⚪ No Change ({len(nochange_out)})",
    ])

    def _render_preview(tab, df, tab_name, limit=_PREVIEW_LIMIT):
        """Render a limited preview of a DataFrame inside a tab."""
        with tab:
            if df.empty:
                st.info(f"No {tab_name} parts found.")
                return

            total = len(df)

            # Comment filter for modified tab
            if tab_name == "modified" and "COMMENTS" in df.columns:
                comment_filter = st.text_input(
                    "🔎 Filter comments (e.g. type 'TORQ' to find torque changes)",
                    value="",
                    key=f"comment_filter_{tab_name}",
                    placeholder="Type to filter within COMMENTS column...",
                )
                if comment_filter.strip():
                    mask = df["COMMENTS"].astype(str).str.upper().str.contains(
                        comment_filter.strip().upper(), na=False
                    )
                    df = df[mask].reset_index(drop=True)
                    total = len(df)
                    st.caption(f"Showing {total} rows matching '{comment_filter}'")

            # Limit preview size
            if total > limit:
                st.caption(f"Showing first {limit} of {total} rows.")
                st.dataframe(df.head(limit), use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)

    _render_preview(tab_mod, modified_out, "modified")
    _render_preview(tab_new, new_out, "new")
    _render_preview(tab_del, deleted_out, "deleted")
    _render_preview(tab_nc,  nochange_out, "no change")

    # ══════════════════════════════════════════════════════════════════════════════
    # ROW ID SEARCH
    # ══════════════════════════════════════════════════════════════════════════════
    # st.divider()
    # st.subheader("🔍 Search by ROW ID")
    # search_row_id = st.text_input(
    #     "Enter ROW ID",
    #     value="",
    #     placeholder="Type a ROW ID to view its full details...",
    #     label_visibility="collapsed",
    # )

    # ══════════════════════════════════════════════════════════════════════════════
    # DEFERRED EXCEL EXPORT — only builds workbook on demand
    # ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("📥 Export Professional Report")

    c_name, c_btn = st.columns([3, 1])

    default_name = generate_comparison_filename()

    with c_name:
        export_filename = st.text_input(
            "Report Filename",
            value=default_name,
            help="You can rename the report before downloading. Default includes today's date."
        )
        if not export_filename.lower().endswith(".xlsx"):
            export_filename += ".xlsx"

    @st.cache_data(show_spinner="Preparing formatted Excel report... This may take a moment.")
    def _prepare_comparison_export(df_nc, df_mod, df_new, df_del):
        return export_comparison_excel(df_nc, df_mod, df_new, df_del)

    with c_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Prepare Download", use_container_width=True, key="prep_comp_btn"):
            st.session_state["comp_export_ready"] = True

        if st.session_state.get("comp_export_ready"):
            export_bytes = _prepare_comparison_export(nochange_out, modified_out, new_out, deleted_out)
            st.download_button(
                label="Download Excel 📊",
                data=export_bytes,
                file_name=export_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
