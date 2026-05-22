import streamlit as st
import pandas as pd
import config
from db import get_all_agents, update_agent, insert_agent

TEAMS = ["Unassigned", "Subaru", "Chevrolet"]

def show():
    if not st.session_state.agent.get("is_admin"):
        st.error("Access denied.")
        st.stop()

    st.title("⚙️ Admin Panel")

    with st.expander("➕ Add New Agent", expanded=False):
        with st.form("add_agent", clear_on_submit=True):
            email = st.text_input("Email address")
            team = st.selectbox("Team", TEAMS)
            dash = st.checkbox("Can view dashboard", value=True)
            if st.form_submit_button("Add Agent", type="primary"):
                if not email.strip():
                    st.warning("Email is required.")
                else:
                    try:
                        insert_agent(email.strip(), team, dash)
                        st.success(f"{email} added!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    st.divider()
    st.subheader("Current Agents")

    agents = get_all_agents()
    if not agents:
        st.info("No agents found.")
        return

    df = pd.DataFrame(agents)
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={
        "email": "Email", "display_name": "Name", "team": "Team",
        "can_view_dashboard": "Dashboard", "is_admin": "Admin",
    })

    edited = st.data_editor(
        df[["Email", "Name", "Team", "Dashboard", "Admin"]],
        column_config={
            "Email": st.column_config.TextColumn("Email", disabled=True, width="large"),
            "Name": st.column_config.TextColumn("Name", disabled=True),
            "Team": st.column_config.SelectboxColumn("Team", options=TEAMS, required=True),
            "Dashboard": st.column_config.CheckboxColumn("Dashboard Access"),
            "Admin": st.column_config.CheckboxColumn("Admin"),
        },
        hide_index=True, use_container_width=True, key="admin_editor",
    )

    if st.button("💾 Save Changes", type="primary"):
        orig = df[["Email", "Team", "Dashboard", "Admin"]].set_index("Email")
        new = edited.set_index("Email")
        count = 0
        for email, row in new.iterrows():
            o = orig.loc[email]
            if (row["Team"] != o["Team"] or row["Dashboard"] != o["Dashboard"] or row["Admin"] != o["Admin"]):
                try:
                    update_agent(email, row["Team"], bool(row["Dashboard"]), bool(row["Admin"]))
                    count += 1
                except Exception as e:
                    st.error(f"Failed to update {email}: {e}")
        if count:
            st.success(f"Updated {count} agent(s).")
            st.rerun()
        else:
            st.info("No changes.")
