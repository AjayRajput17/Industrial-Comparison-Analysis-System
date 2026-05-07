"""
config.py — Build streamlit-authenticator config from Streamlit Secrets.

Reads credentials and cookie settings from st.secrets (backed by
.streamlit/secrets.toml locally, or the Streamlit Cloud Secrets UI
in production) and returns the dict expected by stauth.Authenticate.
"""

import streamlit as st


def get_auth_config() -> dict:
    """
    Build the config dict that streamlit-authenticator expects.

    Reads from st.secrets which maps to:
      - .streamlit/secrets.toml  (local development)
      - Streamlit Cloud Secrets  (production deployment)

    Returns
    -------
    dict with keys: 'credentials', 'cookie'
    """
    secrets = st.secrets

    # ── Cookie / session config ────────────────────────────────────────────
    cookie_config = {
        "name":        secrets["cookie"]["name"],
        "key":         secrets["cookie"]["key"],
        "expiry_days": secrets["cookie"]["expiry_days"],
    }

    # ── Credentials ────────────────────────────────────────────────────────
    # st.secrets stores TOML tables as AttrDict; we need plain dicts
    # for streamlit-authenticator.
    usernames = {}
    for username, user_data in secrets["credentials"]["usernames"].items():
        usernames[username] = {
            "email":      user_data["email"],
            "first_name": user_data["first_name"],
            "last_name":  user_data["last_name"],
            "password":   user_data["password"],
        }

    credentials = {"usernames": usernames}

    return {
        "credentials": credentials,
        "cookie":      cookie_config,
    }
