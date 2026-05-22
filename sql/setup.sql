-- Run these statements manually in a Snowflake worksheet to initialize the database.
-- Make sure you are using the correct warehouse, database, and schema.

ALTER SESSION SET TIMEZONE = 'America/Denver';

CREATE TABLE IF NOT EXISTS agents (
    email VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255),
    team VARCHAR(50) DEFAULT 'Unassigned',
    can_view_dashboard BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS call_logs (
    log_id INTEGER AUTOINCREMENT,
    agent_email VARCHAR(255),
    call_type VARCHAR(20),
    appointment BOOLEAN,
    logged_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    logged_date DATE DEFAULT CURRENT_DATE(),
    PRIMARY KEY (log_id)
);

CREATE TABLE IF NOT EXISTS edit_logs (
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
);

-- Seed your first admin (replace with your email)
-- INSERT INTO agents (email, display_name, team, can_view_dashboard, is_admin)
-- VALUES ('you@company.com', 'Your Name', 'Unassigned', TRUE, TRUE);
