import streamlit as st
import config
from auth import get_authorization_url, handle_oauth_callback
from db import get_agent_by_email, init_tables
from views.logger import show as show_logger
from views.dashboard import show as show_dashboard
from views.admin import show as show_admin

st.set_page_config(page_title=config.APP_NAME, layout="wide", page_icon="📞")

if "init" not in st.session_state:
    try:
        init_tables()
        st.session_state.init = True
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()

if "code" in st.query_params and "user" not in st.session_state:
    user_info = handle_oauth_callback()
    st.query_params.clear()
    if user_info:
        email = user_info.get("email", "")
        if not email:
            st.error("Could not retrieve email from Google.")
            st.stop()
        agent = get_agent_by_email(email)
        if agent:
            agent = {k.lower(): v for k, v in agent.items()}
            st.session_state.user = user_info
            st.session_state.agent = agent
            st.rerun()
        else:
            st.error("Access denied. Your email is not registered.")
            st.stop()
    else:
        st.stop()

if "user" not in st.session_state:
    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;align-items:center;min-height:80vh;flex-direction:column;text-align:center">
            <h1 style="font-size:3rem;margin-bottom:0">📞</h1>
            <h1>{config.APP_NAME}</h1>
            <p style="color:#888;margin-bottom:2rem">Sign in with Google Workspace</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.link_button("🔑 Sign in with Google", get_authorization_url(), use_container_width=True)
    st.stop()

agent = st.session_state.agent

with st.sidebar:
    u = st.session_state.user
    if u.get("picture"):
        st.image(u["picture"], width=60)
    st.markdown(f"**{agent.get('display_name', u.get('name', ''))}**")
    st.caption(f"{u.get('email', '')}  ·  {agent.get('team', 'Unassigned')}")
    st.divider()

    if "page" not in st.session_state:
        st.session_state.page = "Logger"

    opts = ["📞 Logger", "📊 Dashboard"]
    if agent.get("is_admin"):
        opts.append("⚙️ Admin")

    sel = st.radio("Navigation", opts, key="nav_radio")
    st.session_state.page = sel.split(" ", 1)[1]

    st.divider()
    if st.button("🚪 Sign Out", use_container_width=True):
        for k in ["user", "agent", "oauth_state", "page", "init"]:
            st.session_state.pop(k, None)
        st.rerun()

if st.session_state.page == "Logger":
    show_logger()
elif st.session_state.page == "Dashboard":
    show_dashboard()
elif st.session_state.page == "Admin":
    show_admin()
