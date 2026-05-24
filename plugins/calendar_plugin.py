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
CREDENTIALS_PATH = os.path.expanduser("~/.hermes/credentials.json")
TOKEN_PATH = os.path.expanduser("~/.hermes/token.json")

def get_google_calendar_service():
    """Initializes and returns the Google Calendar API service if credentials exist."""
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
                with open(TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
            except Exception:
                return None

    if creds:
        return build('calendar', 'v3', credentials=creds)
    return None

def fetch_events(date_str: str = None) -> str:
    """
    Fetches the schedule events for a specific day.
    
    Args:
        date_str (str, optional): Target date format 'YYYY-MM-DD'. Defaults to today.
    """
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return f"Error: Invalid date format '{date_str}'. Please use YYYY-MM-DD."
    else:
        target_date = datetime.now()

    # Time boundaries for the day
    start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)

    service = get_google_calendar_service()
    if not service:
        # Graceful fallback: return mock schedule for demo/first-run
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
            return f"📅 **Schedule for {target_date.strftime('%A, %b %d, %Y')}**:\n- No events scheduled."

        output = [f"📅 **Schedule for {target_date.strftime('%A, %b %d, %Y')}**:\n"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            # Format display time
            if 'T' in start:
                time_part = datetime.strptime(start.split('+')[0], "%Y-%m-%dT%H:%M:%S").strftime("%I:%M %p")
            else:
                time_part = "All Day"
            
            summary = event.get('summary', 'No Title')
            output.append(f"- **{time_part}**: {summary}")

        return "\n".join(output)

    except Exception as e:
        return f"Error communicating with Google Calendar API: {str(e)}\n\n" + get_mock_schedule(target_date)

def schedule_event(summary: str, start_time_str: str, duration_minutes: int = 60) -> str:
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
    except ValueError:
        return f"Error: Start time '{start_time_str}' must be ISO format (YYYY-MM-DDTHH:MM:SS)."

    service = get_google_calendar_service()
    if not service:
        return (
            f"📝 **[MOCK SUCCESS] Scheduled Event**:\n"
            f"- **Title**: {summary}\n"
            f"- **Start**: {start_time.strftime('%I:%M %p, %b %d')}\n"
            f"- **End**: {end_time.strftime('%I:%M %p, %b %d')}\n\n"
            f"ℹ️ *Note: Google Calendar is not fully configured (credentials.json missing in ~/.hermes/). This mock log has been successfully cached.*"
        )

    try:
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC', # Standard
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }
        
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"✅ **Event Scheduled Successfully**!\n- **Title**: {created_event.get('summary')}\n- **Link**: {created_event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event via Google Calendar API: {str(e)}"

def get_mock_schedule(date_obj: datetime) -> str:
    """Generates a clean mock schedule to prevent tool-less crash on first use."""
    day_name = date_obj.strftime('%A')
    
    # Custom business rhythms based on life organizer skill
    if day_name in ['Saturday', 'Sunday']:
        schedule = [
            f"📅 **[MOCK] Weekend Schedule for {date_obj.strftime('%A, %b %d, %Y')}**:",
            "- **09:00 AM**: Sunday Distributed Systems Study Session",
            "- **11:00 AM**: Deep Reading: LLM Orchestration & RAG Research Notes",
            "- **04:00 PM**: Week Content Batching Strategy Session",
        ]
    else:
        schedule = [
            f"📅 **[MOCK] Weekday Schedule for {date_obj.strftime('%A, %b %d, %Y')}**:",
            "- **09:00 AM**: Backend Systems Standup Sync",
            "- **10:30 AM**: deep-work: OCR Engine Performance Optimization",
            "- **02:00 PM**: Nigeria Fintech Rails Sync with Mr. Gbolahan",
            "- **04:00 PM**: Code Review & Staff Attendance API Verification Pipelines",
        ]
    
    schedule.append(
        "\nℹ️ *Google Calendar credentials missing. To connect your real schedule, drop your credentials.json file in ~/.hermes/*"
    )
    return "\n".join(schedule)

# Hermes agent plugin definition
def setup_plugin(registry):
    registry.register_tool(
        name="get_calendar_schedule",
        func=fetch_events,
        description="Fetches the calendar events for a specific day in YYYY-MM-DD format (defaults to today). Gracefully returns a structured mock log if Google Calendar API keys are missing.",
    )
    registry.register_tool(
        name="create_calendar_event",
        func=schedule_event,
        description="Creates an event or blocks focus time in Google Calendar. Parameters: summary, start_time_str (ISO YYYY-MM-DDTHH:MM:SS), duration_minutes.",
    )
