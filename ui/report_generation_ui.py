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
        "Recreate existing comparison report formats directly from MBOMs by detecting the true data headers."
        "</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    col_ref, col_raw = st.columns(2)

    with col_ref:
        st.subheader("🎯 1. Target Template")
        st.info("Upload the existing 'Golden Template' (e.g., 'New report...'). The generated report will clone this exact column schema.")
        reference_file = st.file_uploader("Upload reference report", type=["xlsx", "xls"], key="ref_file")

    with col_raw:
        st.subheader("📥 2. Raw MBOM Data")
        st.info("Upload the raw engineering BOM (e.g., 'TORQUE_CURRENT_REPORT.xlsx').")
        raw_file = st.file_uploader("Upload raw Excel file", type=["xlsx", "xls", "csv"], key="raw_file")

    @st.cache_data(show_spinner="Running Business Header Detection & Building Report...")
    def _cached_build(raw, ref):
        return build_business_report_from_raw(raw, ref)

    if raw_file and reference_file:
        raw_bytes = raw_file.getvalue()
        ref_bytes = reference_file.getvalue()

        try:
            # Build business report
            df_report, info = _cached_build(raw_bytes, ref_bytes)

            st.success("✅ Report Generation Complete! Columns directly matched without semantic mapping.")

            # Show diagnostics
            with st.expander("🔍 Processing Diagnostics & Data Flow Trace", expanded=True):
                st.write(f"**Target Report Data Constraints**")
                st.write(f"- Schema Size Found: **{info['target_columns_count']} specific fields**")
                
                st.divider()
                st.write(f"**MBOM Header Detection Phase**")
                st.write(f"- True Header detected at Row Index: **{info['detected_header_row_index']}**")
                st.write(f"- Total Rows Extracted: **{info['rows_generated']}**")

                st.divider()
                st.write(f"**Column Mapping Phase**")
                st.write(f"- Directly mapped target fields: **{len(info['matched_fields'])}**")
                
                # Use columns to show mapped vs unmapped neatly
                c_map, c_miss = st.columns(2)
                with c_map:
                    st.markdown("**Successfully Mapped Fields:**")
                    for m in info['matched_fields']:
                        st.write(f"- `{m}`")
                
                with c_miss:
                    st.markdown("**Synthesized Blank Columns:**")
                    if info['unmatched_fields']:
                        for m in info['unmatched_fields']:
                            st.write(f"- `{m}`")
                    else:
                        st.write("_None, all target schema columns existed in MBOM!_")
                        
                st.divider()
                st.write("**Row ID Generation Engine:** active")

            st.subheader("Preview Business-Ready Data")
            # Show only top rows
            st.dataframe(df_report.head(50))

            # Download button
            st.divider()
            st.subheader("📤 3. Export Comparison-Ready Report")

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_report.to_excel(writer, index=False, sheet_name="Report")
            output.seek(0)

            st.download_button(
                label="Download Report for Comparison System 📥",
                data=output,
                file_name=f"Generated_{raw_file.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
