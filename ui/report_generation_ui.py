import streamlit as st
import pandas as pd
import io
from report_generator.builder import build_business_report_from_raw


def render():
    st.markdown(
        "<h1 style='text-align:center;'>📄 EBOM/MBOM Business Report Generator</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#888;'>"
        "Generate comparison-compatible reports directly from raw MBOMs. "
        "Business filters and deduplication are applied automatically."
        "</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    col_raw, col_ref = st.columns(2)

    with col_raw:
        st.subheader("📥 1. Raw MBOM Data")
        st.info("Upload the raw engineering BOM (e.g., 'TORQUE_CURRENT_REPORT.xlsx').")
        raw_file = st.file_uploader("Upload raw Excel file", type=["xlsx", "xls", "csv"], key="raw_file")

    with col_ref:
        st.subheader("🎯 2. Target Template (Optional)")
        st.info("Upload an existing report to clone its schema. If skipped, the default schema is used.")
        reference_file = st.file_uploader("Upload reference report (optional)", type=["xlsx", "xls"], key="ref_file")

    @st.cache_data(show_spinner="Running Business Pipeline (Header Detection → Filtering → Deduplication → Mapping)...")
    def _cached_build(raw, ref):
        return build_business_report_from_raw(raw, ref)

    if raw_file:
        raw_bytes = raw_file.getvalue()
        ref_bytes = reference_file.getvalue() if reference_file else None

        try:
            df_report, info = _cached_build(raw_bytes, ref_bytes)

            st.success("✅ Report Generation Complete!")

            # ══════════════════════════════════════════════════════════════
            # PIPELINE TRACE DIAGNOSTICS
            # ══════════════════════════════════════════════════════════════
            with st.expander("🔍 Processing Diagnostics & Data Flow Trace", expanded=True):

                # --- Header Detection ---
                st.markdown("#### 📂 Header Detection")
                st.write(f"- True Header detected at Row Index: **{info.get('detected_header_row_index', 'N/A')}**")
                st.write(f"- Total rows loaded from MBOM: **{info.get('rows_after_header_detection', 'N/A')}**")
                st.write(f"- Normalized column count: **{info.get('normalized_raw_columns_count', 'N/A')}**")

                st.divider()

                # --- Schema Source ---
                st.markdown("#### 📋 Target Schema")
                st.write(f"- Schema source: **{info.get('schema_source', 'N/A')}**")
                st.write(f"- Schema size: **{info.get('target_columns_count', 'N/A')} columns**")

                st.divider()

                # --- Business Filtering ---
                st.markdown("#### 🎛️ Business Filtering")
                st.write(f"- Rows before all filters: **{info.get('rows_before_all_filters', 'N/A')}**")

                # PART STATUS
                st.write(f"- **PART STATUS filter** (keep='R')")
                st.write(f"  - Column: `{info.get('filter_part_status_col', 'N/A')}`")
                st.write(f"  - Removed: **{info.get('rows_removed_part_status', 0)}** rows")

                # TORQUE SAFETY
                st.write(f"- **TORQUE SAFETY filter** (keep='Y','N')")
                st.write(f"  - Column: `{info.get('filter_torque_safety_col', 'N/A')}`")
                st.write(f"  - Removed: **{info.get('rows_removed_torque_safety', 0)}** rows")

                # TRGT
                st.write(f"- **TRGT filter** (keep 0 and ≥5, remove 0<x<5)")
                st.write(f"  - Column: `{info.get('filter_trgt_col', 'N/A')}`")
                st.write(f"  - Removed: **{info.get('rows_removed_trgt', 0)}** rows")

                st.write(f"- **Rows after all filters: {info.get('rows_after_all_filters', 'N/A')}**")
                st.write(f"- Total filtered out: **{info.get('total_rows_filtered_out', 0)}** rows")

                st.divider()

                # --- Column Mapping ---
                st.markdown("#### 🔗 Column Mapping")
                st.write(f"- Directly mapped fields: **{len(info.get('matched_fields', []))}**")

                c_map, c_miss = st.columns(2)
                with c_map:
                    st.markdown("**Successfully Mapped:**")
                    for m in info.get('matched_fields', []):
                        st.write(f"- `{m}`")
                with c_miss:
                    st.markdown("**Synthesized Blank:**")
                    unmapped = info.get('unmatched_fields', [])
                    if unmapped:
                        for m in unmapped:
                            st.write(f"- `{m}`")
                    else:
                        st.write("_None — all target columns mapped!_")

                st.divider()

                # --- Deduplication ---
                st.markdown("#### 🧹 Business Deduplication")
                st.write(f"- Dedup columns used: `{info.get('dedup_columns_used', 'N/A')}`")
                st.write(f"- Rows before deduplication: **{info.get('total_rows_pre_dedupe', 'N/A')}**")
                st.write(f"- Business duplicates removed: **{info.get('exact_duplicates_to_remove', 0)}**")

                st.divider()

                # --- Row ID & Validation ---
                st.markdown("#### 🆔 Row ID Generation & Validation")
                st.write(f"- Rows after deduplication: **{info.get('total_rows_post_dedupe', 'N/A')}**")
                st.write(f"- Conflicting ROW IDs remaining: **{info.get('conflicting_rowids_remaining', 0)}**")

                validation_status = info.get('validation_status', '')
                if info.get('conflicting_rowids_remaining', 0) > 0:
                    st.warning(validation_status)
                    st.write(f"- Sample conflicts: {info.get('sample_conflicting_rowids', [])}")
                else:
                    st.success(f"✅ {validation_status}")

                st.divider()

                # --- Final Export ---
                st.markdown("#### 📊 Final Report")
                st.write(f"- Final row count: **{info.get('rows_generated', 'N/A')}**")
                st.write(f"- Final column count: **{len(info.get('final_report_schema', []))}**")

            # ══════════════════════════════════════════════════════════════
            # PREVIEW
            # ══════════════════════════════════════════════════════════════
            st.subheader("Preview Business-Ready Data")
            st.dataframe(df_report.head(50))

            # ══════════════════════════════════════════════════════════════
            # EXPORT
            # ══════════════════════════════════════════════════════════════
            st.divider()
            st.subheader("📥 3. Export Comparison-Ready Report")

            from exports.report_generation_export.report_exporter import export_business_report_excel
            from exports.report_generation_export.report_filename import generate_report_filename

            c_name, c_btn = st.columns([3, 1])

            default_name = generate_report_filename()

            with c_name:
                export_filename = st.text_input(
                    "Report Filename",
                    value=default_name,
                    help="You can rename the report before downloading. Default includes today's date."
                )
                if not export_filename.lower().endswith(".xlsx"):
                    export_filename += ".xlsx"

            @st.cache_data(show_spinner="Applying formatting and building workbook...")
            def _prepare_report_export(df):
                return export_business_report_excel(df)

            with c_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Prepare Download", use_container_width=True, key="prep_rep_btn"):
                    st.session_state["rep_export_ready"] = True

                if st.session_state.get("rep_export_ready"):
                    output_bytes = _prepare_report_export(df_report)
                    st.download_button(
                        label="Download Report 📊",
                        data=output_bytes,
                        file_name=export_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
            st.exception(e)
