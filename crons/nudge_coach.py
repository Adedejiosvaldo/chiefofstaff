import sys
import os
from datetime import datetime, timedelta

# Resolve core plugins path
plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../plugins'))
if plugins_dir not in sys.path:
    sys.path.insert(0, plugins_dir)

if os.path.exists('/opt/data/plugins') and '/opt/data/plugins' not in sys.path:
    sys.path.insert(0, '/opt/data/plugins')

try:
    from core import db, todoist, calendar
except ImportError:
    try:
        from plugins.core import db, todoist, calendar
    except ImportError as e:
        print(f"Import warning in nudge_coach: {e}")


def run_nudge_coach():
    print("Fetching active/overdue tasks from Todoist...")
    tasks_summary = todoist.fetch_todoist_tasks("today | overdue")

    if "No active or overdue tasks" in tasks_summary:
        print("All tasks clear today! No accountability nudge required.")
        return

    print("Fetching tomorrow's schedule from Google Calendar...")
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    calendar_summary = calendar.fetch_events(tomorrow_str)

    gamification_stats = db.get_gamification_stats()
    streak = gamification_stats.get("global_streak", 0)
    hearts = gamification_stats.get("hearts", 5)

    prompt = (
        "It is 5:00 PM Lagos time. Here is an active audit of outstanding commitments:\n\n"
        f"Accountability Stats: {streak}-Day Streak 🔥 | {hearts}/5 Hearts 💖\n\n"
        f"{tasks_summary}\n\n"
        "Tomorrow's Calendar:\n"
        f"{calendar_summary}\n\n"
        "INSTRUCTIONS:\n"
        "Render an assertive, encouraging 5:00 PM Evening Accountability Card. "
        "Highlight pending commitments, find an open block on tomorrow's calendar for deep work, "
        "and present exactly 3 numbered 1-touch reply options:\n"
        "1️⃣ Book tomorrow's free morning block for deep work\n"
        "2️⃣ Mark task done right now (+10 XP)\n"
        "3️⃣ Snooze task to tomorrow 9:00 AM\n\n"
        "If Hearts <= 2, apply Duo the Owl's persistent, slightly humorous warning."
    )

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    model_crons = os.environ.get("LLM_MODEL_CRONS", "deepseek/deepseek-chat")

    if api_key:
        print(f"Using OpenRouter hybrid compilation via '{model_crons}'...")
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            system_instruction = (
                "You are Oya, Joseph's proactive Accountability Coach. "
                "Format output as a scannable Executive Card with emojis and 1-touch actions."
            )
            base_url = "https://openrouter.ai/api/v1/chat/completions"
            if os.environ.get("DEEPSEEK_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
                base_url = "https://api.deepseek.com/v1/chat/completions"

            payload = {
                "model": model_crons,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5
            }
            response = requests.post(base_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            compiled_text = response.json()["choices"][0]["message"]["content"]
            prompt = f"[DELIVER DIRECTLY]: {compiled_text}"
            print("Successfully pre-compiled Accountability Nudge!")
        except Exception as e:
            print(f"OpenRouter compilation warning: {e}. Falling back to raw prompt queueing.")

    notification_id = db.add_notification(prompt)
    print(f"Accountability nudge queued successfully! (Notification ID: {notification_id})")


if __name__ == "__main__":
    try:
        run_nudge_coach()
    except Exception as e:
        print(f"Error executing nudge coach: {e}")
