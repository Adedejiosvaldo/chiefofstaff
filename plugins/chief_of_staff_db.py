import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.expanduser("~/.hermes/chief_of_staff.db")

def get_db_connection():
    """Returns a connection to the SQLite database, creating directories if needed."""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create notifications table for outbound reminders/cron jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending', 'processing', 'sent', 'failed')) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Create telemetry table for routine responses & self-training loops
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL, -- JSON string of telemetry payload
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 3. Create opportunities table for the global scraper cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            type TEXT CHECK(type IN ('job', 'scholarship', 'course', 'coupon', 'other')) NOT NULL,
            description TEXT,
            status TEXT CHECK(status IN ('unread', 'sent', 'applied', 'ignored')) DEFAULT 'unread',
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 4. Create habits table for active accountability tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_name TEXT NOT NULL,
            status TEXT CHECK(status IN ('completed', 'failed', 'snoozed')) NOT NULL,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# --- Notifications Helpers ---

def add_notification(prompt: str) -> int:
    """Queues a new notification prompt to be sent via WhatsApp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (prompt, status) VALUES (?, 'pending')",
        (prompt,)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_pending_notifications():
    """Fetches all pending notifications."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE status = 'pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_notification_status(notification_id: int, status: str):
    """Updates the delivery state of a notification."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE notifications SET status = ? WHERE id = ?",
        (status, notification_id)
    )
    conn.commit()
    conn.close()

# --- Telemetry & Analytics Helpers ---

def log_telemetry(event_type: str, details: dict):
    """Logs behavior metrics for the adaptive self-training routines."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO telemetry (event_type, details) VALUES (?, ?)",
        (event_type, json.dumps(details))
    )
    conn.commit()
    conn.close()

def get_recent_telemetry(limit: int = 100):
    """Pulls recent telemetry logs for analysis."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM telemetry ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Global Opportunities Helpers ---

def add_opportunity(title: str, url: str, opp_type: str, description: str) -> bool:
    """Adds a newly scraped opportunity to the database. Returns True if new, False if duplicate."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO opportunities (title, url, type, description, status) VALUES (?, ?, ?, ?, 'unread')",
            (title, url, opp_type, description)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # Opportunity already existed (url is UNIQUE)
        success = False
    conn.close()
    return success

def get_unread_opportunities(limit: int = 10):
    """Retrieves unread opportunities to display to the user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM opportunities WHERE status = 'unread' ORDER BY discovered_at DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_opportunity_status(opp_id: int, status: str):
    """Updates opportunity state (e.g. read, applied, ignored)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE opportunities SET status = ? WHERE id = ?",
        (status, opp_id)
    )
    conn.commit()
    conn.close()

# Initialize DB on load
try:
    init_db()
except Exception as e:
    print(f"Error initializing DB: {e}")
