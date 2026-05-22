import streamlit as st
import requests
import secrets
from urllib.parse import urlencode

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_authorization_url():
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]

    state = secrets.token_urlsafe(32)
    st.session_state.oauth_state = state

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

def handle_oauth_callback():
    code = st.query_params.get("code")
    state = st.query_params.get("state")

    if not code:
        return None

    token_data = {
        "code": code,
        "client_id": st.secrets["google_oauth"]["client_id"],
        "client_secret": st.secrets["google_oauth"]["client_secret"],
        "redirect_uri": st.secrets["google_oauth"]["redirect_uri"],
        "grant_type": "authorization_code",
    }

    resp = requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=15)
    if not resp.ok:
        st.error("Failed to authenticate with Google.")
        return None

    tokens = resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        st.error("No access token returned.")
        return None

    headers = {"Authorization": f"Bearer {access_token}"}
    user_resp = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=15)
    if not user_resp.ok:
        st.error("Failed to retrieve user info.")
        return None

    return user_resp.json()
