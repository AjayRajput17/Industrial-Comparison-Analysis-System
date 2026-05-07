"""
app.py — Streamlit UI for the Industrial Comparison Analysis System.

Two-file upload flow: OLD report + NEW report.
Composite key matching, rule-based comments, 4 output categories.
Protected by session-based authentication (streamlit-authenticator).
"""

import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
from auth.config import get_auth_config
from modules.ingestion import load_file
from modules.analysis import analyze_file_structure, normalize_columns
from modules.comparator import compare_datasets
from modules.comment_engine import (
    PRIORITY_FIELDS,
    generate_comments_batch,
)
from modules.exporter import export_excel

# ── Page config (must be the FIRST Streamlit call) ─────────────────────────────
st.set_page_config(page_title="FCS Analysis", layout="wide")


# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

auth_config = get_auth_config()

authenticator = stauth.Authenticate(
    auth_config["credentials"],
    auth_config["cookie"]["name"],
    auth_config["cookie"]["key"],
    auth_config["cookie"]["expiry_days"],
    auto_hash=False,  # passwords are already bcrypt-hashed in secrets.toml
)

# If not authenticated, show a centered login page with heading at the top
if not st.session_state.get("authentication_status"):
    st.markdown(
        "<h1 style='text-align:center; margin-top: 3rem; margin-bottom: 0.5rem;'>"
        "🔧 Industrial Comparison Analysis System"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#888; font-size: 1.1rem; margin-bottom: 2.5rem;'>"
        "Secure Access Portal"
        "</p>",
        unsafe_allow_html=True,
    )
    
    # Use columns to center the login form (1 part empty, 1.5 parts form, 1 part empty)
    _, col_login, _ = st.columns([1, 1.5, 1])
    
    with col_login:
        try:
            authenticator.login()
        except Exception as e:
            st.error(f"Authentication error: {e}")
            
        if st.session_state.get("authentication_status") is False:
            st.error("❌ Username or password is incorrect.")
            
    # If still not authenticated after the form (or haven't submitted yet), stop here
    if not st.session_state.get("authentication_status"):
        st.stop()
else:
    # If already authenticated, we still must call login() so the library validates the cookie on page refresh
    try:
        authenticator.login()
    except Exception as e:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATED — user has logged in successfully
# ══════════════════════════════════════════════════════════════════════════════

# ── Sidebar: welcome message + logout button ──────────────────────────────────
st.sidebar.markdown(f"### 👤 Welcome, **{st.session_state.get('name')}**")
st.sidebar.caption(f"Logged in as: `{st.session_state.get('username')}`")
authenticator.logout("🚪 Logout", "sidebar")
st.sidebar.divider()

# ── App header ─────────────────────────────────────────────────────────────────
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
    st.stop()


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
    if st.button("⚡ Important Only", use_container_width=True):
        st.session_state["selected_fields"] = [
            f for f in PRIORITY_FIELDS if f in all_data_cols
        ]
    if st.button("📋 All Fields", use_container_width=True):
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


def _search_by_row_id(frames_with_labels, search_term):
    """Search across all result DataFrames by ROW ID."""
    if not search_term.strip():
        return None
    term = search_term.strip().upper()
    for label, frame in frames_with_labels:
        if frame.empty:
            continue
        norm_frame, _ = normalize_columns(frame)
        for candidate in ["ROW ID", "ROW_ID", "ROWID", "ROW NO", "ROW_NO"]:
            if candidate in norm_frame.columns:
                mask = norm_frame[candidate].astype(str).str.strip().str.upper() == term
                if mask.any():
                    idx = mask.values.argmax()
                    return label, frame.iloc[idx]
    return None


if search_row_id.strip():
    result = _search_by_row_id(
        [("⚪ No Change", nochange_out),
         ("🟡 Modified", modified_out),
         ("🟢 New", new_out),
         ("🔴 Deleted", deleted_out)],
        search_row_id,
    )

    if result:
        category, row = result
        st.markdown(f"**Category:** {category}")

        # Split row into data fields vs COMMENTS
        data_fields = {}
        comment_value = ""
        for col_name, value in row.items():
            if str(col_name).upper() == "COMMENTS":
                comment_value = str(value) if not (isinstance(value, float) and pd.isna(value)) else ""
            else:
                data_fields[col_name] = value

        # Show data fields as a single-row table
        row_df = pd.DataFrame([data_fields])
        st.dataframe(row_df, width="stretch", hide_index=True)

        # Show COMMENTS line-by-line below the table
        if comment_value.strip():
            st.markdown("**📝 COMMENTS (changes):**")
            for line in comment_value.split("\n"):
                if line.strip():
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔸 `{line.strip()}`")
    else:
        st.warning(f"No row found with ROW ID = '{search_row_id}'")


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
excel_data = export_excel(nochange_out, modified_out, new_out, deleted_out)
st.download_button(
    "📥 Download Excel Report",
    data=excel_data,
    file_name="comparison_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
