import os
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

# Support both standard host installation (~/.hermes/) and official Docker volume mount (/opt/data/)
if os.path.exists("/opt/data"):
    DB_PATH = "/opt/data/chief_of_staff.db"
else:
    DB_PATH = os.path.expanduser("~/.hermes/chief_of_staff.db")


@contextmanager
def get_db_cursor(commit: bool = False):
    """Context manager for SQLite database operations ensuring connections are safely closed."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        cursor = conn.cursor()
        yield cursor
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    """Initializes the SQLite database schema with indexes and initial state."""
    with get_db_cursor(commit=True) as cursor:
        # 1. Notifications table for outbound reminders/cron jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                status TEXT CHECK(status IN ('pending', 'processing', 'sent', 'failed')) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);")

        # 2. Telemetry table for routine responses & self-training loops
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at);")

        # 3. Opportunities table for the global scraper cache
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_opps_status ON opportunities(status);")

        # 4. Habits table for active accountability tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_name TEXT NOT NULL,
                status TEXT CHECK(status IN ('completed', 'failed', 'snoozed', 'deferred', 'excused', 'missed')) NOT NULL,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Gamification user stats table
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

        # 6. Habit streaks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gamification_habit_streaks (
                habit_name TEXT PRIMARY KEY,
                streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                total_completions INTEGER DEFAULT 0
            )
        """)

        # 7. Achievements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gamification_achievements (
                badge_name TEXT PRIMARY KEY,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. Dynamic on-the-fly trivia table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trivia_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                explanation TEXT,
                status TEXT DEFAULT 'unanswered',
                user_answer TEXT,
                evaluation_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed default user stats if not already present
        cursor.execute("SELECT COUNT(*) FROM gamification_user_stats WHERE user_id = 'default_user'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO gamification_user_stats (user_id, xp, level, streak_freezes, hearts, global_streak, longest_streak)
                VALUES ('default_user', 0, 1, 2, 5, 0, 0)
            """)


# --- Notifications Helpers ---

def add_notification(prompt: str) -> int:
    """Queues a new notification prompt in the database."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO notifications (prompt, status) VALUES (?, 'pending')",
            (prompt,)
        )
        return cursor.lastrowid


def get_pending_notifications():
    """Fetches all pending notifications in FIFO order."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM notifications WHERE status = 'pending' ORDER BY created_at ASC")
        return [dict(row) for row in cursor.fetchall()]


def update_notification_status(notification_id: int, status: str):
    """Updates the delivery state of a notification."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "UPDATE notifications SET status = ? WHERE id = ?",
            (status, notification_id)
        )


# --- Telemetry & Analytics Helpers ---

def log_telemetry(event_type: str, details: dict):
    """Logs behavior metrics for the adaptive self-training routines."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO telemetry (event_type, details) VALUES (?, ?)",
            (event_type, json.dumps(details))
        )


def get_recent_telemetry(days: int = 14, limit: int = 100):
    """Pulls recent telemetry logs within a rolling sliding window of days."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM telemetry WHERE datetime(created_at) >= datetime('now', ?) ORDER BY created_at DESC LIMIT ?",
            (f"-{days} days", limit)
        )
        return [dict(row) for row in cursor.fetchall()]


# --- Global Opportunities Helpers ---

def add_opportunity(title: str, url: str, opp_type: str, description: str) -> bool:
    """Adds a newly scraped opportunity to the database. Returns True if new, False if duplicate."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "INSERT INTO opportunities (title, url, type, description, status) VALUES (?, ?, ?, ?, 'unread')",
                (title, url, opp_type, description)
            )
            return True
    except sqlite3.IntegrityError:
        return False


def get_unread_opportunities(limit: int = 10):
    """Retrieves unread opportunities."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM opportunities WHERE status = 'unread' ORDER BY discovered_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


def update_opportunity_status(opp_id: int, status: str):
    """Updates opportunity state (e.g. read, applied, ignored, sent)."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "UPDATE opportunities SET status = ? WHERE id = ?",
            (status, opp_id)
        )


# --- Gamification Helpers ---

def get_gamification_stats() -> dict:
    """Fetches global user stats, active streaks, and achievements."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM gamification_user_stats WHERE user_id = 'default_user'")
        row = cursor.fetchone()
        stats = dict(row) if row else {
            "user_id": "default_user", "xp": 0, "level": 1, "streak_freezes": 2,
            "hearts": 5, "global_streak": 0, "longest_streak": 0, "last_active_date": None
        }

        cursor.execute("SELECT * FROM gamification_habit_streaks ORDER BY streak DESC")
        stats["streaks"] = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT badge_name FROM gamification_achievements ORDER BY unlocked_at ASC")
        stats["achievements"] = [r["badge_name"] for r in cursor.fetchall()]

        return stats


def update_gamification_stats(xp: int = None, level: int = None, streak_freezes: int = None,
                             hearts: int = None, global_streak: int = None, longest_streak: int = None,
                             last_active_date: str = None):
    """Updates one or more global user stats fields."""
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
        with get_db_cursor(commit=True) as cursor:
            query = f"UPDATE gamification_user_stats SET {', '.join(fields)} WHERE user_id = 'default_user'"
            cursor.execute(query, tuple(values))


def get_habit_streak(habit_name: str) -> dict:
    """Fetches a specific habit's streak, initializing if not present."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT * FROM gamification_habit_streaks WHERE habit_name = ?", (habit_name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO gamification_habit_streaks (habit_name, streak, best_streak, total_completions) VALUES (?, 0, 0, 0)",
                (habit_name,)
            )
            return {"habit_name": habit_name, "streak": 0, "best_streak": 0, "total_completions": 0}
        return dict(row)


def update_habit_streak(habit_name: str, streak: int, best_streak: int, total_completions: int):
    """Updates streak metrics for a specific habit."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE gamification_habit_streaks
            SET streak = ?, best_streak = ?, total_completions = ?
            WHERE habit_name = ?
        """, (streak, best_streak, total_completions, habit_name))


def log_habit_event(habit_name: str, status: str):
    """Logs a single habit check-in event."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO habits (habit_name, status) VALUES (?, ?)",
            (habit_name, status)
        )


def unlock_achievement(badge_name: str) -> bool:
    """Locks/unlocks an achievement badge. Returns True if newly unlocked, False if already had it."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("INSERT INTO gamification_achievements (badge_name) VALUES (?)", (badge_name,))
            return True
    except sqlite3.IntegrityError:
        return False


def get_unlocked_achievements() -> list:
    """Gets all unlocked badge names."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT badge_name FROM gamification_achievements")
        return [row["badge_name"] for row in cursor.fetchall()]


def reset_weekly_hearts():
    """Resets user hearts to full capacity (5 hearts)."""
    update_gamification_stats(hearts=5)


# --- Dynamic Trivia Challenges ---

def save_trivia_challenge(category: str, question: str, options: list, correct_option: str, explanation: str) -> int:
    """Saves a newly generated dynamic trivia question in SQLite."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            INSERT INTO trivia_challenges (category, question, options, correct_option, explanation, status)
            VALUES (?, ?, ?, ?, ?, 'unanswered')
        """, (category, question, json.dumps(options), correct_option, explanation))
        return cursor.lastrowid


def get_trivia_challenge(challenge_id: int) -> dict:
    """Fetches a specific trivia challenge by ID."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM trivia_challenges WHERE id = ?", (challenge_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["options"] = json.loads(res["options"]) if isinstance(res["options"], str) else res["options"]
        return res


def update_trivia_challenge_result(challenge_id: int, user_answer: str, is_correct: bool, feedback: str):
    """Records the user's answer and the AI's brutal evaluation feedback."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE trivia_challenges
            SET user_answer = ?, status = ?, evaluation_feedback = ?
            WHERE id = ?
        """, (user_answer, "correct" if is_correct else "incorrect", feedback, challenge_id))


# Auto-initialize DB on import
try:
    init_db()
except Exception as e:
    print(f"Warning: Database initialization exception: {e}")
