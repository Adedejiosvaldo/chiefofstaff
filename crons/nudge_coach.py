import sys
import os
from datetime import datetime, timedelta

# Append the plugins path so we can import our db and integrations
sys.path.append(os.path.expanduser('~/.hermes/plugins'))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../plugins')))

try:
    import chief_of_staff_db
    import todoist_plugin
    import calendar_plugin
    IMPORTS_OK = True
except ImportError as e:
    print(f"Import warning in development: {e}")
    IMPORTS_OK = False

def run_nudge_coach():
    if not IMPORTS_OK:
        print("Cannot run nudge coach: Required plugins could not be imported.")
        return

    print("Fetching active/overdue tasks from Todoist...")
    tasks_summary = todoist_plugin.fetch_todoist_tasks("today | overdue")
    
    # If the user has absolutely no active or overdue tasks, skip the nudge
    if "No active or overdue tasks" in tasks_summary:
        print("No outstanding tasks found. Skipping accountability nudge.")
        return

    print("Fetching tomorrow's schedule from Google Calendar...")
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    calendar_summary = calendar_plugin.fetch_events(tomorrow_str)

    # Build a highly custom prompt for the agent to render a premium WhatsApp accountability card
    prompt = (
        "It is 5:00 PM Lagos time. Here is an active audit of my outstanding commitments:\n\n"
        f"{tasks_summary}\n\n"
        "Here is my calendar schedule for tomorrow:\n"
        f"{calendar_summary}\n\n"
        "Please send a proactive WhatsApp notification to the user's phone. Act as my assertive, "
        "encouraging Accountability Coach and Chief of Staff. Note any outstanding tasks due today "
        "and nudge me to complete them. Review my calendar for tomorrow and proactively identify "
        "any free blocks of time where I can tackle these tasks. Suggest a specific free time block "
        "and offer to schedule a deep-work sprint for it.\n\n"
        "Present the nudge with clear formatting, using premium spacing and emojis. "
        "At the end of your message, present exactly three clear, numbered choices I can reply with:\n"
        "1. Book the suggested calendar block tomorrow for deep work.\n"
        "2. Snooze this task to tomorrow morning.\n"
        "3. Mark this task as completed now."
    )

    # Queue the prompt in the notifications table
    notification_id = chief_of_staff_db.add_notification(prompt)
    print(f"Accountability nudge successfully queued in SQLite! (Notification ID: {notification_id})")

if __name__ == "__main__":
    try:
        run_nudge_coach()
    except Exception as e:
        print(f"Error executing accountability nudge coach: {e}")
