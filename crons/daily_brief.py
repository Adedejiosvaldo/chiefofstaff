import sys
import os
from datetime import datetime

# Resolve core plugins path
plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../plugins'))
if plugins_dir not in sys.path:
    sys.path.insert(0, plugins_dir)

if os.path.exists('/opt/data/plugins') and '/opt/data/plugins' not in sys.path:
    sys.path.insert(0, '/opt/data/plugins')

try:
    from core import db, todoist, calendar, git_activity, opportunity
except ImportError:
    from plugins.core import db, todoist, calendar, git_activity, opportunity


def run_daily_brief():
    print("Fetching active/overdue tasks from Todoist...")
    tasks_summary = todoist.fetch_todoist_tasks("today | overdue")

    print("Fetching today's schedule from Google Calendar...")
    calendar_summary = calendar.fetch_events()

    print("Fetching recent Git activity...")
    git_summary = git_activity.get_local_git_commits(since_hours=24)

    print("Fetching unread global opportunities...")
    unread_opps = db.get_unread_opportunities(limit=3)
    opps_summary = "📁 **Global Opportunities Radar:**\n"
    if unread_opps:
        for idx, opp in enumerate(unread_opps, 1):
            opps_summary += f"{idx}. **[{opp['type'].upper()}]** {opp['title']} - {opp['url']}\n"
    else:
        opps_summary += "- No new unread opportunities today.\n"

    gamification_stats = db.get_gamification_stats()
    xp = gamification_stats.get("xp", 0)
    level = gamification_stats.get("level", 1)
    streak = gamification_stats.get("global_streak", 0)
    hearts = gamification_stats.get("hearts", 5)

    today_str = datetime.now().strftime("%A, %b %d")

    prompt = (
        f"Generate my Morning Executive Briefing card for {today_str}.\n"
        "Act as my proactive Chief of Staff and Accountability Coach (Oya).\n\n"
        "Raw Data Collected:\n"
        f"Stats: Level {level}, {xp} XP, {streak}-day Streak, {hearts}/5 Hearts\n\n"
        f"{calendar_summary}\n\n"
        f"{tasks_summary}\n\n"
        f"{git_summary}\n\n"
        f"{opps_summary}\n\n"
        "FORMATTING INSTRUCTIONS:\n"
        "Format as a high-density, scannable Executive Card with clear visual hierarchy:\n"
        "1. Top Banner: Date, Level, Streak 🔥, Hearts 💖.\n"
        "2. 📅 Today's Schedule: Clear chronological breakdown.\n"
        "3. 📋 Top 3 Priorities: Filtered from Todoist.\n"
        "4. ✍️ LinkedIn Pre-Draft: Punchy, scroll-stopping post based on recent git commits and backend focus, strictly following Joseph Adewunmi style (Under the Hood, named analogies, punchy rhythm).\n"
        "5. ⚡ 1-Touch Quick Actions at bottom:\n"
        "   Reply 1️⃣: Ship LinkedIn draft to Buffer\n"
        "   Reply 2️⃣: Block 90-min deep work on calendar\n"
        "   Reply 3️⃣: Log priority task completed\n\n"
        "Keep it punchy. No corporate throat-clearing."
    )

    # Hybrid Model Routing (DeepSeek-V3 / Gemini Flash via OpenRouter)
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
                "You are Oya, Joseph's proactive Chief of Staff and Accountability Coach. "
                "Render the final Executive Briefing Card exactly as requested."
            )

            # Load writer voice style guide if available
            voice_path = os.path.expanduser("~/.hermes/skills/writing/writer-voice/SKILL.md")
            if not os.path.exists(voice_path):
                voice_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../skills/writing/writer-voice/SKILL.md"))
            if os.path.exists(voice_path):
                with open(voice_path, "r", encoding="utf-8") as f:
                    system_instruction += "\n\nStyle Guide:\n" + f.read()

            base_url = "https://openrouter.ai/api/v1/chat/completions"
            if os.environ.get("DEEPSEEK_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
                base_url = "https://api.deepseek.com/v1/chat/completions"

            payload = {
                "model": model_crons,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.6
            }
            response = requests.post(base_url, headers=headers, json=payload, timeout=35)
            response.raise_for_status()
            compiled_text = response.json()["choices"][0]["message"]["content"]
            prompt = f"[DELIVER DIRECTLY]: {compiled_text}"
            print("Successfully pre-compiled Executive Briefing!")
        except Exception as e:
            print(f"OpenRouter compilation warning: {e}. Falling back to raw prompt queueing.")

    notification_id = db.add_notification(prompt)
    print(f"Daily Briefing queued successfully! (Notification ID: {notification_id})")


if __name__ == "__main__":
    try:
        run_daily_brief()
    except Exception as e:
        print(f"Error executing daily brief: {e}")
