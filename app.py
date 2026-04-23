
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
