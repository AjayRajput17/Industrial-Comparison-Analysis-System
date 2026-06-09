"""
app.py — Streamlit UI for the Industrial Comparison Analysis System.

Main routing shell and Authentication layer.
Protected by session-based authentication (streamlit-authenticator).
"""

import streamlit as st
import streamlit_authenticator as stauth
from auth.config import get_auth_config
from ui.comparison_ui import render as render_comparison
from ui.report_generation_ui import render as render_report_generation

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
            
    # If still not authenticated after the form, stop here
    if not st.session_state.get("authentication_status"):
        st.stop()
else:
    # If already authenticated, validate cookie on refresh
    try:
        authenticator.login()
    except Exception as e:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING & SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

st.sidebar.markdown(f"### 👤 Welcome, **{st.session_state.get('name')}**")
st.sidebar.caption(f"Logged in as: `{st.session_state.get('username')}`")

st.sidebar.divider()
st.sidebar.markdown("### 🧭 Navigation")
page = st.sidebar.radio("Go to", ["Report Generation", "Comparison Engine"], label_visibility="collapsed")
st.sidebar.divider()

authenticator.logout("🚪 Logout", "sidebar")

if page == "Comparison Engine":
    render_comparison()
elif page == "Report Generation":
    render_report_generation()
