-- backend/src/database/migrations/042_processed_job_alert_emails.sql
CREATE TABLE IF NOT EXISTS processed_job_alert_emails (
    message_id TEXT PRIMARY KEY,
    sender TEXT,
    subject TEXT,
    processed_at REAL NOT NULL
);
