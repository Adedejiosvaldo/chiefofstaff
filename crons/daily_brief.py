import sys
import os
from datetime import datetime

# Append the plugins path so we can import our db and integrations
sys.path.append(os.path.expanduser('~/.hermes/plugins'))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../plugins')))

try:
    import chief_of_staff_db
    import todoist_plugin
    import calendar_plugin
    import git_plugin
    IMPORTS_OK = True
except ImportError as e:
    print(f"Import warning in development: {e}")
    IMPORTS_OK = False

def run_daily_brief():
    if not IMPORTS_OK:
        print("Cannot run daily brief: Required plugins could not be imported.")
        return

    print("Fetching active/overdue tasks from Todoist...")
    tasks_summary = todoist_plugin.fetch_todoist_tasks("today | overdue")

    print("Fetching today's schedule from Google Calendar...")
    calendar_summary = calendar_plugin.fetch_events()

    print("Fetching recent Git activity...")
    git_summary = git_plugin.get_local_git_commits(since_hours=24)

    print("Fetching unread global opportunities...")
    unread_opps = chief_of_staff_db.get_unread_opportunities(limit=5)
    opps_summary = "📁 **Global Opportunity Radar matches:**\n"
    if unread_opps:
        for idx, opp in enumerate(unread_opps, 1):
            opps_summary += f"{idx}. **[{opp['type'].upper()}]** {opp['title']} - {opp['url']}\n"
    else:
        opps_summary += "- No new unread opportunities matching backend or AI found.\n"

    # Build a highly custom prompt for the agent to render a premium WhatsApp Daily Briefing card
    prompt = (
        "Please generate my Daily Briefing card. Act as my Life Organizer and chief of staff.\n\n"
        "Here is the raw data collected locally:\n\n"
        f"{calendar_summary}\n\n"
        f"{tasks_summary}\n\n"
        f"{git_summary}\n\n"
        f"{opps_summary}\n\n"
        "Please synthesize this into a premium, beautiful daily briefing. "
        "Include a summary of today's schedule, highlight critical pending actions, "
        "and pre-draft a highly punchy, scroll-stopping LinkedIn post based on my recent git activity "
        "and backend/AI focus, strictly adhering to the Joseph Adewunmi Writing Style Guide.\n\n"
        "Format the message with clean headers, premium spacing, and visual emojis."
    )

    # OpenRouter hybrid model routing configuration
    api_key = os.environ.get("OPENROUTER_API_KEY")
    model_crons = os.environ.get("LLM_MODEL_CRONS", "google/gemini-2.0-flash")

    if api_key:
        print(f"Using OpenRouter hybrid compilation via '{model_crons}'...")
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            # Inject writer voice context if available
            system_instruction = "You are the user's Chief of Staff. Compile the requested message in the user's exact writing style and tone."
            voice_path = os.path.expanduser("~/.hermes/skills/writer-voice.md")
            if not os.path.exists(voice_path):
                voice_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../skills/writer-voice.md"))
            if os.path.exists(voice_path):
                with open(voice_path, "r", encoding="utf-8") as f:
                    system_instruction += "\n\nFollow these style guidelines:\n" + f.read()

            payload = {
                "model": model_crons,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
            }
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=35)
            response.raise_for_status()
            compiled_text = response.json()["choices"][0]["message"]["content"]
            prompt = f"[DELIVER DIRECTLY]: {compiled_text}"
            print("Successfully pre-compiled Daily Briefing with OpenRouter Flash!")
        except Exception as e:
            print(f"OpenRouter compilation warning: {e}. Falling back to raw prompt queueing.")

    # Queue the prompt in the notifications table
    notification_id = chief_of_staff_db.add_notification(prompt)
    print(f"Daily Briefing successfully queued in SQLite! (Notification ID: {notification_id})")

if __name__ == "__main__":
    try:
        run_daily_brief()
    except Exception as e:
        print(f"Error executing daily brief: {e}")
