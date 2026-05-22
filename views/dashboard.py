import streamlit as st
import pandas as pd
import plotly.express as px
import config
from db import (
    get_leaderboard_today,
    get_leaderboard_month,
    get_dod,
    get_mom,
    get_monthly_totals,
    get_call_logs_export,
)

TEAM_COLORS = {"Subaru": config.SUBARU_BLUE, "Chevrolet": config.CHEVY_GOLD}

def show():
    st.title("📊 Dashboard & Leaderboard")

    tab_daily, tab_monthly, tab_overview, tab_export = st.tabs(["Daily", "Month-to-Date", "Month-over-Month", "Export CSV"])

    with tab_daily:
        _show_daily()

    with tab_monthly:
        _show_monthly()

    with tab_overview:
        _show_overview()

    with tab_export:
        _show_export()

def _show_daily():
    rows = get_leaderboard_today()

    if not rows:
        st.info("No calls logged today.")
        return

    df = pd.DataFrame(rows)
    df.columns = [c.lower() for c in df.columns]

    st.subheader(f"🏆 Leaderboard — {pd.Timestamp.now(tz=config.MT_TZ).strftime('%B %d, %Y')}")

    d = df[["display_name", "team", "inbound", "outbound", "total_calls", "appointments"]].copy()
    d["appt_%"] = (d["appointments"] / d["total_calls"] * 100).round(0).fillna(0).astype(int).astype(str) + "%"
    d.columns = ["Agent", "Team", "Inbound", "Outbound", "Calls", "Appts", "Appt %"]
    st.dataframe(d, hide_index=True, use_container_width=True)

    fig = px.bar(
        df,
        x="display_name", y="appointments",
        color="team", color_discrete_map=TEAM_COLORS,
        title="Daily Appointments by Agent",
        labels={"display_name": "", "appointments": "Appointments", "team": ""},
        text="appointments",
    )
    fig.update_layout(bargap=0.3, xaxis_tickangle=-45, legend_title_text="")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    dod = get_dod()
    if dod:
        st.subheader("📈 Day-over-Day")
        dod_df = pd.DataFrame(dod)
        dod_df.columns = [c.lower() for c in dod_df.columns]
        t = dod_df[dod_df["period"] == "Today"]
        y = dod_df[dod_df["period"] == "Yesterday"]
        if not t.empty and not y.empty:
            tc, ta = int(t.iloc[0]["calls"]), int(t.iloc[0]["appointments"])
            yc, ya = int(y.iloc[0]["calls"]), int(y.iloc[0]["appointments"])
            mc = (tc - yc) / max(yc, 1) * 100
            ma = (ta - ya) / max(ya, 1) * 100
            cols = st.columns(4)
            cols[0].metric("Today Calls", tc, f"{mc:+.0f}%")
            cols[1].metric("Today Appointments", ta, f"{ma:+.0f}%")
            cols[2].metric("Yesterday Calls", yc)
            cols[3].metric("Yesterday Appointments", ya)

def _show_monthly():
    rows = get_leaderboard_month()

    if not rows:
        st.info("No calls logged this month.")
        return

    df = pd.DataFrame(rows)
    df.columns = [c.lower() for c in df.columns]

    month_name = pd.Timestamp.now(tz=config.MT_TZ).strftime("%B")
    st.subheader(f"🏆 Leaderboard — {month_name} (MTD)")

    d = df[["display_name", "team", "total_calls", "appointments"]].copy()
    d["appt_%"] = (d["appointments"] / d["total_calls"] * 100).round(0).fillna(0).astype(int).astype(str) + "%"
    d.columns = ["Agent", "Team", "Calls", "Appts", "Appt %"]
    st.dataframe(d, hide_index=True, use_container_width=True)

    fig = px.bar(
        df,
        x="display_name", y="appointments",
        color="team", color_discrete_map=TEAM_COLORS,
        title=f"{month_name} Appointments by Agent",
        labels={"display_name": "", "appointments": "Appointments", "team": ""},
        text="appointments",
    )
    fig.update_layout(bargap=0.3, xaxis_tickangle=-45, legend_title_text="")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    mom = get_mom()
    if mom:
        st.subheader("📈 Month-over-Month")
        mom_df = pd.DataFrame(mom)
        mom_df.columns = [c.lower() for c in mom_df.columns]
        c = mom_df[mom_df["period"] == "Current Month"]
        p = mom_df[mom_df["period"] == "Last Month"]
        if not c.empty and not p.empty:
            cc, ca = int(c.iloc[0]["calls"]), int(c.iloc[0]["appointments"])
            pc, pa = int(p.iloc[0]["calls"]), int(p.iloc[0]["appointments"])
            mc = (cc - pc) / max(pc, 1) * 100
            ma = (ca - pa) / max(pa, 1) * 100
            cols = st.columns(4)
            cols[0].metric(f"{month_name} Calls", cc, f"{mc:+.0f}%")
            cols[1].metric(f"{month_name} Appointments", ca, f"{ma:+.0f}%")
            cols[2].metric("Last Month Calls", pc)
            cols[3].metric("Last Month Appointments", pa)

def _show_overview():
    rows = get_monthly_totals()

    if not rows:
        st.info("No historical data yet.")
        return

    df = pd.DataFrame(rows)
    df.columns = [c.lower() for c in df.columns]
    df["month"] = pd.to_datetime(df["month"])
    df["month_label"] = df["month"].dt.strftime("%B %Y")

    st.subheader("📅 Calendar Month Totals")

    d = df[["month_label", "team", "display_name", "total_calls", "appointments"]].copy()
    d["appt_%"] = (d["appointments"] / d["total_calls"] * 100).round(0).fillna(0).astype(int).astype(str) + "%"
    d.columns = ["Month", "Team", "Agent", "Calls", "Appts", "Appt %"]
    st.dataframe(d, hide_index=True, use_container_width=True)

    fig = px.bar(
        df,
        x="month_label", y="appointments", color="display_name",
        barmode="group",
        title="Monthly Appointments by Agent",
        labels={"month_label": "", "appointments": "Appointments", "display_name": ""},
    )
    fig.update_layout(bargap=0.2, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

def _show_export():
    st.subheader("📥 Export Call Logs")

    col_a, col_b = st.columns(2)
    with col_a:
        start = st.date_input("Start date", value=None)
    with col_b:
        end = st.date_input("End date", value=None)

    rows = get_call_logs_export(start_date=start, end_date=end)

    if not rows:
        st.info("No logs found for the selected date range.")
        return

    df = pd.DataFrame(rows)
    df.columns = [c.lower() for c in df.columns]
    df["appointment"] = df["appointment"].apply(lambda x: "Yes" if x else "No")
    df["logged_at"] = pd.to_datetime(df["logged_at"]).dt.strftime("%Y-%m-%d %I:%M %p")
    df["logged_date"] = pd.to_datetime(df["logged_date"]).dt.strftime("%Y-%m-%d")

    csv = df[[
        "log_id", "agent", "team", "agent_email", "call_type",
        "appointment", "logged_date", "logged_at",
    ]].to_csv(index=False)

    st.caption(f"{len(df)} rows")
    st.download_button(
        label="⬇ Download CSV",
        data=csv,
        file_name=f"call_logs_{start or 'all'}_{end or 'all'}.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )
