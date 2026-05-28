import streamlit as st
from datetime import datetime
import pytz
import config
from db import log_call, get_recent_logs, get_log_by_id, edit_log

mtz = pytz.timezone(config.MT_TZ)

def show():
    agent = st.session_state.agent
    email = agent["email"]

    st.title("📞 Call Logger")
    st.caption(f"Logged in as **{agent['display_name']}** · {agent['team']}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        call_type = st.radio(
            "Call Type",
            ["Inbound", "Outbound"],
            horizontal=True,
            index=1,
            key="call_type",
            label_visibility="collapsed",
        )

    with col2:
        appointment_type = st.radio(
            "Appointment Type",
            [None, "Main Shop", "Express Service"],
            format_func=lambda x: "No Appointment" if x is None else x,
            horizontal=True,
            key="appointment_type",
            label_visibility="collapsed",
        )

    st.markdown(
        f"""
        <div style="text-align: center; font-size: 1.1rem; margin-bottom: 0.5rem;">
            <strong>{call_type}</strong>
            ·
            {"✅ " + appointment_type if appointment_type else "❌ No Appointment"}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("💾 Save Call", type="primary", use_container_width=True):
        try:
            log_call(email, call_type, appointment_type)
            st.toast("Call saved!", icon="✅")
            if "call_type" in st.session_state:
                del st.session_state["call_type"]
            if "appointment_type" in st.session_state:
                del st.session_state["appointment_type"]
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save call: {e}")

    st.divider()
    st.subheader("Recent Calls")
    recent = get_recent_logs(email, limit=10)

    if not recent:
        st.info("No calls logged yet today.")
        return

    for row in recent:
        logged_at = row["LOGGED_AT"]
        if isinstance(logged_at, datetime):
            age_seconds = (datetime.now(mtz) - mtz.localize(logged_at)).total_seconds()
        else:
            age_seconds = 99999

        age_minutes = age_seconds / 60
        can_edit = age_minutes < config.EDIT_WINDOW_MINUTES

        cols = st.columns([2, 1.2, 0.8, 0.8, 1.2])
        with cols[0]:
            time_str = mtz.localize(logged_at).strftime("%I:%M %p") if isinstance(logged_at, datetime) else str(logged_at)
            st.text(time_str)
        with cols[1]:
            st.text("📥 Inbound" if row["CALL_TYPE"] == "Inbound" else "📤 Outbound")
        with cols[2]:
            val = row["APPOINTMENT_TYPE"]
            st.text(val if val else "—")
        with cols[3]:
            st.text(f"{int(age_minutes)}m" if can_edit else "")
        with cols[4]:
            if can_edit:
                if st.button("✏️", key=f"e_{row['LOG_ID']}", use_container_width=True):
                    st.session_state.editing_log = row["LOG_ID"]
                    st.rerun()

        if st.session_state.get("editing_log") == row["LOG_ID"]:
            with st.container(border=True):
                log = get_log_by_id(row["LOG_ID"])
                if not log:
                    continue

                st.caption("Edit entry (reason required)")
                nc = st.radio(
                    "Type", ["Inbound", "Outbound"],
                    index=0 if log["CALL_TYPE"] == "Inbound" else 1,
                    horizontal=True, key=f"et_{row['LOG_ID']}",
                )
                current_appt = log.get("APPOINTMENT_TYPE")
                na = st.radio(
                    "Appt", [None, "Main Shop", "Express Service"],
                    index=0 if current_appt is None else (1 if current_appt == "Main Shop" else 2),
                    format_func=lambda x: "No Appointment" if x is None else x,
                    horizontal=True, key=f"ea_{row['LOG_ID']}",
                )
                reason = st.text_area("Reason for edit", key=f"er_{row['LOG_ID']}")

                sc, cc = st.columns(2)
                with sc:
                    if st.button("Save Edit", type="primary", key=f"se_{row['LOG_ID']}"):
                        if not reason.strip():
                            st.warning("Please provide a reason.")
                        else:
                            try:
                                edit_log(
                                    row["LOG_ID"], email,
                                    log["CALL_TYPE"], nc,
                                    log["APPOINTMENT_TYPE"], na,
                                    reason.strip(),
                                )
                                st.toast("Call updated!", icon="✏️")
                                del st.session_state.editing_log
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to edit: {e}")
                with cc:
                    if st.button("Cancel", key=f"ce_{row['LOG_ID']}"):
                        del st.session_state.editing_log
                        st.rerun()
