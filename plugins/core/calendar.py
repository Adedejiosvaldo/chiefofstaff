import os
import sys
from datetime import datetime, timedelta

# Google Calendar API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Persistent volume or home directory credential paths
CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_CREDENTIALS_PATH",
    "/opt/data/credentials.json" if os.path.exists("/opt/data") else os.path.expanduser("~/.hermes/credentials.json")
)
TOKEN_PATH = os.environ.get(
    "GOOGLE_TOKEN_PATH",
    "/opt/data/token.json" if os.path.exists("/opt/data") else os.path.expanduser("~/.hermes/token.json")
)


def get_google_calendar_service():
    """Initializes and returns the Google Calendar API service if authorized."""
    if not GOOGLE_LIBS_AVAILABLE:
        return None

    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0, open_browser=False)
                with open(TOKEN_PATH, 'w') as token_file:
                    token_file.write(creds.to_json())
            except Exception:
                return None

    if creds:
        return build('calendar', 'v3', credentials=creds)
    return None


def get_mock_schedule(date_obj: datetime) -> str:
    """Generates a clean mock schedule for testing/unconfigured environments."""
    day_name = date_obj.strftime('%A')

    if day_name in ['Saturday', 'Sunday']:
        schedule = [
            f"📅 **Schedule for {date_obj.strftime('%A, %b %d, %Y')}**:",
            "- **09:00 AM**: Sunday Distributed Systems Study Session",
            "- **11:30 AM**: Deep Reading: LLM Orchestration & RAG Research Notes",
            "- **04:00 PM**: Weekly Content Batching Strategy",
        ]
    else:
        schedule = [
            f"📅 **Schedule for {date_obj.strftime('%A, %b %d, %Y')}**:",
            "- **09:00 AM**: Backend Systems Standup Sync",
            "- **10:30 AM**: [Deep Work] OCR Engine Optimization (90m)",
            "- **02:00 PM**: Fintech Rails Review w/ Mr. Gbolahan",
            "- **04:30 PM**: Code Review & Staff Attendance API Verification",
        ]

    return "\n".join(schedule)


def fetch_events(date_str: str = None) -> str:
    """
    Fetches Google Calendar events for a given date string (YYYY-MM-DD) or today.

    Args:
        date_str (str, optional): Target date format 'YYYY-MM-DD'.
    """
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return f"Error: Invalid date format '{date_str}'. Please use YYYY-MM-DD."
    else:
        target_date = datetime.now()

    start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)

    service = get_google_calendar_service()
    if not service:
        return get_mock_schedule(target_date)

    try:
        time_min = start_of_day.isoformat() + 'Z'
        time_max = end_of_day.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        if not events:
            return f"📅 **Schedule for {target_date.strftime('%A, %b %d, %Y')}**:\n- No events scheduled. Clear day for deep work! 🚀"

        output = [f"📅 **Schedule for {target_date.strftime('%A, %b %d, %Y')}**:\n"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                try:
                    time_part = datetime.strptime(start.split('+')[0], "%Y-%m-%dT%H:%M:%S").strftime("%I:%M %p")
                except Exception:
                    time_part = start.split('T')[1][:5]
            else:
                time_part = "All Day"

            summary = event.get('summary', 'No Title')
            output.append(f"- **{time_part}**: {summary}")

        return "\n".join(output)

    except Exception as e:
        return f"Error communicating with Google Calendar API: {str(e)}\n\n" + get_mock_schedule(target_date)


def schedule_event(summary: str = "", start_time_str: str = "", duration_minutes: int = 60) -> str:
    """
    Creates an event in Google Calendar.

    Args:
        summary (str): Event title.
        start_time_str (str): Start ISO time e.g., '2026-05-24T14:00:00'.
        duration_minutes (int): Event duration in minutes.
    """
    try:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = start_time + timedelta(minutes=duration_minutes)
    except Exception as e:
        return f"Error: Start time '{start_time_str}' must be in ISO format (YYYY-MM-DDTHH:MM:SS). Details: {e}"

    service = get_google_calendar_service()
    if not service:
        return (
            f"📝 **[MOCK SUCCESS] Scheduled Calendar Event**:\n"
            f"- **Title**: {summary}\n"
            f"- **Start**: {start_time.strftime('%I:%M %p, %b %d')}\n"
            f"- **End**: {end_time.strftime('%I:%M %p, %b %d')}\n\n"
            f"ℹ️ *Note: Google Calendar token not found. Mock event logged successfully.*"
        )

    try:
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Africa/Lagos',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Africa/Lagos',
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"✅ **Event Booked**!\n- **Title**: {created_event.get('summary')}\n- **Link**: {created_event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event via Google Calendar API: {str(e)}"
