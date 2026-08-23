"""
Backwards-compatibility shim for chief_of_staff_db module.
All operations are routed to the unified plugins.core.db module.
"""
from core.db import (
    DB_PATH,
    get_db_cursor,
    init_db,
    add_notification,
    get_pending_notifications,
    update_notification_status,
    log_telemetry,
    get_recent_telemetry,
    add_opportunity,
    get_unread_opportunities,
    update_opportunity_status,
    get_gamification_stats,
    update_gamification_stats,
    get_habit_streak,
    update_habit_streak,
    log_habit_event,
    unlock_achievement,
    get_unlocked_achievements,
    reset_weekly_hearts,
)
import sqlite3

def get_db_connection():
    """Legacy helper returning a raw SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn
