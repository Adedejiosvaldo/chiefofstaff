import os
import sqlite3
import json
from datetime import datetime

# Support both standard host installation (~/.hermes/) and official Docker volume mount (/opt/data/)
if os.path.exists("/opt/data"):
    DB_PATH = "/opt/data/chief_of_staff.db"
else:
    DB_PATH = os.path.expanduser("~/.hermes/chief_of_staff.db")

def get_db_connection():
    """Returns a connection to the SQLite database, creating directories if needed."""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode and set a busy timeout of 5 seconds to handle concurrent writes
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
    except Exception as e:
        print(f"Database performance PRAGMA warning: {e}")
        
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
    
    # 5. Create gamification_user_stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamification_user_stats (
            user_id TEXT PRIMARY KEY DEFAULT 'default_user',
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            streak_freezes INTEGER DEFAULT 2,
            hearts INTEGER DEFAULT 5,
            global_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_active_date TEXT
        )
    """)

    # 6. Create gamification_habit_streaks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamification_habit_streaks (
            habit_name TEXT PRIMARY KEY,
            streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            total_completions INTEGER DEFAULT 0
        )
    """)

    # 7. Create gamification_achievements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamification_achievements (
            badge_name TEXT PRIMARY KEY,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed default user stats if not already present
    cursor.execute("SELECT COUNT(*) FROM gamification_user_stats WHERE user_id = 'default_user'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO gamification_user_stats (user_id, xp, level, streak_freezes, hearts, global_streak, longest_streak)
            VALUES ('default_user', 0, 1, 2, 5, 0, 0)
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

def get_recent_telemetry(days: int = 14, limit: int = 100):
    """Pulls recent telemetry logs for analysis within a rolling sliding window of days."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM telemetry WHERE datetime(created_at) >= datetime('now', ?) ORDER BY created_at DESC LIMIT ?",
        (f"-{days} days", limit)
    )
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

# --- Gamification Helpers ---

def get_gamification_stats() -> dict:
    """Fetches global user stats, active streaks, and achievements."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch user stats
    cursor.execute("SELECT * FROM gamification_user_stats WHERE user_id = 'default_user'")
    row = cursor.fetchone()
    stats = dict(row) if row else {
        "user_id": "default_user", "xp": 0, "level": 1, "streak_freezes": 2, 
        "hearts": 5, "global_streak": 0, "longest_streak": 0, "last_active_date": None
    }
    
    # 2. Fetch all habit streaks
    cursor.execute("SELECT * FROM gamification_habit_streaks ORDER BY streak DESC")
    stats["streaks"] = [dict(r) for r in cursor.fetchall()]
    
    # 3. Fetch achievements
    cursor.execute("SELECT badge_name FROM gamification_achievements ORDER BY unlocked_at ASC")
    stats["achievements"] = [r["badge_name"] for r in cursor.fetchall()]
    
    conn.close()
    return stats

def update_gamification_stats(xp: int = None, level: int = None, streak_freezes: int = None, 
                             hearts: int = None, global_streak: int = None, longest_streak: int = None, 
                             last_active_date: str = None):
    """Updates one or more global user stats fields."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    fields = []
    values = []
    if xp is not None:
        fields.append("xp = ?")
        values.append(xp)
    if level is not None:
        fields.append("level = ?")
        values.append(level)
    if streak_freezes is not None:
        fields.append("streak_freezes = ?")
        values.append(streak_freezes)
    if hearts is not None:
        fields.append("hearts = ?")
        values.append(hearts)
    if global_streak is not None:
        fields.append("global_streak = ?")
        values.append(global_streak)
    if longest_streak is not None:
        fields.append("longest_streak = ?")
        values.append(longest_streak)
    if last_active_date is not None:
        fields.append("last_active_date = ?")
        values.append(last_active_date)
        
    if fields:
        query = f"UPDATE gamification_user_stats SET {', '.join(fields)} WHERE user_id = 'default_user'"
        cursor.execute(query, tuple(values))
        conn.commit()
    conn.close()

def get_habit_streak(habit_name: str) -> dict:
    """Fetches a specific habit's streak and completion stats, initializing if not present."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gamification_habit_streaks WHERE habit_name = ?", (habit_name,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute(
            "INSERT INTO gamification_habit_streaks (habit_name, streak, best_streak, total_completions) VALUES (?, 0, 0, 0)",
            (habit_name,)
        )
        conn.commit()
        stats = {"habit_name": habit_name, "streak": 0, "best_streak": 0, "total_completions": 0}
    else:
        stats = dict(row)
        
    conn.close()
    return stats

def update_habit_streak(habit_name: str, streak: int, best_streak: int, total_completions: int):
    """Updates the streak records for a specific habit."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE gamification_habit_streaks 
        SET streak = ?, best_streak = ?, total_completions = ? 
        WHERE habit_name = ?
    """, (streak, best_streak, total_completions, habit_name))
    conn.commit()
    conn.close()

def unlock_achievement(badge_name: str) -> bool:
    """Locks/unlocks an achievement badge. Returns True if successfully unlocked, False if already had it."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO gamification_achievements (badge_name) VALUES (?)", (badge_name,))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_unlocked_achievements() -> list:
    """Gets all unlocked badge names."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT badge_name FROM gamification_achievements")
    badges = [row["badge_name"] for row in cursor.fetchall()]
    conn.close()
    return badges

def reset_weekly_hearts():
    """Resets user hearts to full capacity (5 hearts) for a new week."""
    update_gamification_stats(hearts=5)

# Initialize DB on load
try:
    init_db()
except Exception as e:
    print(f"Error initializing DB: {e}")

