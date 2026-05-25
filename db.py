import snowflake.connector
from snowflake.connector import DictCursor
import streamlit as st
from datetime import datetime, timedelta, date
import config

def _schema():
    db = st.secrets["snowflake"].get("database", "CALL_LOGGER_DB")
    sch = st.secrets["snowflake"].get("schema", "PAYROLL")
    return f"{db}.{sch}"

def get_conn():
    cfg = {k: v for k, v in st.secrets["snowflake"].items() if v}
    key_pem = cfg.pop("private_key", None)
    if key_pem:
        from cryptography.hazmat.primitives import serialization
        key = serialization.load_pem_private_key(key_pem.encode(), password=None)
        cfg["private_key"] = key
    conn = snowflake.connector.connect(**cfg)
    with conn.cursor() as cur:
        cur.execute(f"USE SCHEMA {_schema()}")
        cur.execute(f"ALTER SESSION SET TIMEZONE = '{config.MT_TZ}'")
    return conn

def query(sql, params=None):
    conn = get_conn()
    try:
        with conn.cursor(DictCursor) as cur:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            if cur.description:
                return cur.fetchall()
            return []
    finally:
        conn.close()

def init_tables():
    conn = get_conn()
    ns = _schema()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {ns}.agents (
                    email VARCHAR(255) PRIMARY KEY,
                    display_name VARCHAR(255),
                    team VARCHAR(50) DEFAULT 'Unassigned',
                    can_view_dashboard BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {ns}.call_logs (
                    log_id INTEGER AUTOINCREMENT,
                    agent_email VARCHAR(255),
                    call_type VARCHAR(20),
                    appointment BOOLEAN,
                    logged_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    logged_date DATE DEFAULT CURRENT_DATE(),
                    PRIMARY KEY (log_id)
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {ns}.edit_logs (
                    edit_id INTEGER AUTOINCREMENT,
                    log_id INTEGER,
                    agent_email VARCHAR(255),
                    old_call_type VARCHAR(20),
                    new_call_type VARCHAR(20),
                    old_appt BOOLEAN,
                    new_appt BOOLEAN,
                    reason VARCHAR(500),
                    edited_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    PRIMARY KEY (edit_id)
                )
            """)
        conn.commit()
    finally:
        conn.close()

def get_agent_by_email(email):
    rows = query("SELECT * FROM agents WHERE email = %s", (email,))
    return rows[0] if rows else None

def create_agent(email, display_name):
    query(
        "INSERT INTO agents (email, display_name) VALUES (%s, %s)",
        (email, display_name)
    )
    return get_agent_by_email(email)

def log_call(agent_email, call_type, appointment):
    query(
        "INSERT INTO call_logs (agent_email, call_type, appointment) VALUES (%s, %s, %s)",
        (agent_email, call_type, appointment)
    )

def get_recent_logs(agent_email, limit=10):
    return query(
        """SELECT log_id, call_type, appointment, logged_at, logged_date
           FROM call_logs
           WHERE agent_email = %s
           ORDER BY logged_at DESC
           LIMIT %s""",
        (agent_email, limit)
    )

def get_log_by_id(log_id):
    rows = query("SELECT * FROM call_logs WHERE log_id = %s", (log_id,))
    return rows[0] if rows else None

def edit_log(log_id, agent_email, old_call_type, new_call_type, old_appt, new_appt, reason):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE call_logs SET call_type = %s, appointment = %s WHERE log_id = %s",
                (new_call_type, new_appt, log_id)
            )
            cur.execute(
                """INSERT INTO edit_logs (log_id, agent_email, old_call_type, new_call_type, old_appt, new_appt, reason)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (log_id, agent_email, old_call_type, new_call_type, old_appt, new_appt, reason)
            )
        conn.commit()
    finally:
        conn.close()

def get_leaderboard_today():
    return query("""
        SELECT a.display_name, a.team,
               SUM(CASE WHEN c.call_type = 'Inbound' THEN 1 ELSE 0 END) AS inbound,
               SUM(CASE WHEN c.call_type = 'Outbound' THEN 1 ELSE 0 END) AS outbound,
               COUNT(*) AS total_calls,
               SUM(CASE WHEN c.appointment = TRUE THEN 1 ELSE 0 END) AS appointments
        FROM agents a
        LEFT JOIN call_logs c ON a.email = c.agent_email AND c.logged_date = CURRENT_DATE
        GROUP BY a.display_name, a.team
        ORDER BY appointments DESC, total_calls DESC
    """)

def get_leaderboard_month():
    return query("""
        SELECT a.display_name, a.team,
               COUNT(*) AS total_calls,
               SUM(CASE WHEN c.appointment = TRUE THEN 1 ELSE 0 END) AS appointments
        FROM agents a
        LEFT JOIN call_logs c ON a.email = c.agent_email
            AND c.logged_date >= DATE_TRUNC('MONTH', CURRENT_DATE)
        GROUP BY a.display_name, a.team
        ORDER BY appointments DESC, total_calls DESC
    """)

def get_dod():
    return query("""
        SELECT
            'Today' AS period,
            COUNT(*) AS calls,
            COALESCE(SUM(CASE WHEN appointment THEN 1 ELSE 0 END), 0) AS appointments
        FROM call_logs
        WHERE logged_date = CURRENT_DATE
        UNION ALL
        SELECT
            'Yesterday',
            COUNT(*),
            COALESCE(SUM(CASE WHEN appointment THEN 1 ELSE 0 END), 0)
        FROM call_logs
        WHERE logged_date = DATEADD(DAY, -1, CURRENT_DATE)
    """)

def get_mom():
    return query("""
        WITH current_month AS (
            SELECT
                COUNT(*) AS calls,
                COALESCE(SUM(CASE WHEN appointment THEN 1 ELSE 0 END), 0) AS appointments
            FROM call_logs
            WHERE logged_date >= DATE_TRUNC('MONTH', CURRENT_DATE)
                AND logged_date <= CURRENT_DATE
        ),
        last_month AS (
            SELECT
                COUNT(*) AS calls,
                COALESCE(SUM(CASE WHEN appointment THEN 1 ELSE 0 END), 0) AS appointments
            FROM call_logs
            WHERE logged_date >= DATE_TRUNC('MONTH', DATEADD(MONTH, -1, CURRENT_DATE))
                AND logged_date <= DATEADD(MONTH, -1, CURRENT_DATE)
                AND DAY(logged_date) <= DAY(CURRENT_DATE)
        )
        SELECT 'Current Month' AS period, * FROM current_month
        UNION ALL
        SELECT 'Last Month' AS period, * FROM last_month
    """)

def get_monthly_totals():
    return query("""
        SELECT
            DATE_TRUNC('MONTH', c.logged_date) AS month,
            a.team,
            a.display_name,
            COUNT(*) AS total_calls,
            SUM(CASE WHEN c.appointment THEN 1 ELSE 0 END) AS appointments
        FROM call_logs c
        JOIN agents a ON c.agent_email = a.email
        GROUP BY month, a.team, a.display_name
        ORDER BY month DESC, appointments DESC
    """)

def get_call_logs_export(start_date=None, end_date=None):
    sql = """SELECT c.log_id, a.display_name AS agent, a.team,
                    c.agent_email, c.call_type, c.appointment,
                    c.logged_at, c.logged_date
             FROM call_logs c
             JOIN agents a ON c.agent_email = a.email"""
    params = []
    conditions = []
    if start_date:
        conditions.append("c.logged_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("c.logged_date <= %s")
        params.append(end_date)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY c.logged_at DESC"
    return query(sql, params)

def get_all_agents():
    return query("SELECT * FROM agents ORDER BY display_name ASC")

def update_agent(email, team, can_view_dashboard, is_admin):
    query(
        "UPDATE agents SET team = %s, can_view_dashboard = %s, is_admin = %s WHERE email = %s",
        (team, can_view_dashboard, is_admin, email)
    )

def insert_agent(email, team, can_view_dashboard):
    query(
        "INSERT INTO agents (email, team, can_view_dashboard) VALUES (%s, %s, %s)",
        (email, team, can_view_dashboard)
    )
