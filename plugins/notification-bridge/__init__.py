import os
import sys
import json
from datetime import datetime

# Import shared core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db


def _fetch_and_mark_notifications() -> str:
    """
    Queries SQLite for pending outbound notifications, marks them sent,
    and returns them formatted for the agent.
    """
    try:
        pending_list = db.get_pending_notifications()
        if not pending_list:
            return "No pending notifications."

        response_parts = ["### PENDING SCHEDULED ALERTS TO PROCESS ###\n"]
        for idx, item in enumerate(pending_list, 1):
            db.update_notification_status(item["id"], "sent")

            db.log_telemetry(
                event_type="notification_processed",
                details={
                    "notification_id": item["id"],
                    "prompt": item["prompt"],
                    "processed_at": datetime.now().isoformat()
                }
            )
            response_parts.append(f"{idx}. [ID: {item['id']}] {item['prompt']}")

        response_parts.append(
            "\nAction required: Please process the above alerts, generate the requested briefings or reminders, and deliver them to the user."
        )
        return "\n".join(response_parts)

    except Exception as e:
        return f"Error fetching notifications from SQLite: {str(e)}"


def _add_notification_tool(prompt: str) -> str:
    """Queues a new notification/reminder in the SQLite database."""
    try:
        notification_id = db.add_notification(prompt)
        return json.dumps({
            "success": True,
            "notification_id": notification_id,
            "message": f"Successfully queued notification with ID: {notification_id}"
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def _get_recent_telemetry_tool(days: int = 14, limit: int = 100) -> str:
    """Retrieves recent telemetry logs."""
    try:
        logs = db.get_recent_telemetry(days=days, limit=limit)
        return json.dumps({
            "success": True,
            "logs": [dict(log) for log in logs]
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def register(ctx):
    """Hermes plugin registration entrypoint for notification bridge."""
    ctx.register_tool(
        name="fetch_pending_notifications",
        toolset="notification-bridge",
        schema={
            "type": "object",
            "description": "Checks the database queue for pending outbound notifications and cron reminders.",
            "properties": {}
        },
        handler=lambda args, **kwargs: _fetch_and_mark_notifications()
    )

    ctx.register_tool(
        name="add_notification",
        toolset="notification-bridge",
        schema={
            "type": "object",
            "description": "Queues a reminder or notification prompt in the database for background delivery.",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt or notification text/reminder to queue."
                }
            },
            "required": ["prompt"]
        },
        handler=lambda args, **kwargs: _add_notification_tool(args["prompt"])
    )

    ctx.register_tool(
        name="get_recent_telemetry",
        toolset="notification-bridge",
        schema={
            "type": "object",
            "description": "Retrieves recent user telemetry and habit events for weekly routine analysis.",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to retrieve (default 14)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of records to retrieve (default 100)."
                }
            }
        },
        handler=lambda args, **kwargs: _get_recent_telemetry_tool(
            args.get("days", 14),
            args.get("limit", 100)
        )
    )
