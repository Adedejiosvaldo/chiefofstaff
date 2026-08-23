import os
import sys

# Import shared core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import calendar as core_calendar


def register(ctx):
    """Hermes plugin registration entrypoint for Google Calendar."""
    ctx.register_tool(
        name="get_calendar_schedule",
        toolset="google-calendar",
        schema={
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "Target date in YYYY-MM-DD format. Defaults to today if omitted."
                }
            }
        },
        handler=lambda args, **kwargs: core_calendar.fetch_events(args.get("date_str"))
    )

    ctx.register_tool(
        name="create_calendar_event",
        toolset="google-calendar",
        schema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Event title."
                },
                "start_time_str": {
                    "type": "string",
                    "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)."
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Event duration in minutes (default 60)."
                }
            },
            "required": ["summary", "start_time_str"]
        },
        handler=lambda args, **kwargs: core_calendar.schedule_event(
            summary=args.get("summary", ""),
            start_time_str=args.get("start_time_str") or args.get("start_time", ""),
            duration_minutes=args.get("duration_minutes", 60)
        )
    )
