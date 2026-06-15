import os
import sys
import json
from datetime import datetime

# Add parent plugins directory so we can import the shared DB module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chief_of_staff_db


def _fetch_and_mark_notifications() -> str:
    """
    Queries the SQLite database for any pending outbound notifications/cron triggers,
    marks them as 'sent', and returns them as a combined prompt for the agent to action.

    Returns:
        str: A formatted string of pending alerts to process, or a message indicating no pending items.
    """
    try:
        pending_list = chief_of_staff_db.get_pending_notifications()
        if not pending_list:
            return "No pending notifications."

        response_parts = ["### PENDING SCHEDULED ALERTS TO PROCESS ###\n"]
        for idx, item in enumerate(pending_list, 1):
            chief_of_staff_db.update_notification_status(item["id"], "sent")

            chief_of_staff_db.log_telemetry(
                event_type="notification_processed",
                details={
                    "notification_id": item["id"],
                    "prompt": item["prompt"],
                    "processed_at": datetime.now().isoformat()
                }
            )
            response_parts.append(f"{idx}. [ID: {item['id']}] {item['prompt']}")

        response_parts.append(
            "\nAction required: Please process the above alerts, generate the requested briefings or reminders, and deliver them to the user in your response."
        )
        return "\n".join(response_parts)

    except Exception as e:
        return f"Error fetching notifications from SQLite: {str(e)}"


def _add_notification_tool(prompt: str) -> str:
    """Queues a new notification/reminder in the SQLite database."""
    try:
        notification_id = chief_of_staff_db.add_notification(prompt)
        return json.dumps({
            "success": True,
            "notification_id": notification_id,
            "message": f"Successfully queued notification with ID: {notification_id}"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def _get_recent_telemetry_tool(days: int = 14, limit: int = 100) -> str:
    """Retrieves recent system and user compliance telemetry logs."""
    try:
        logs = chief_of_staff_db.get_recent_telemetry(days=days, limit=limit)
        return json.dumps({
            "success": True,
            "logs": [dict(log) for log in logs]
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def register(ctx):
    """Hermes plugin registration entrypoint."""
    ctx.register_tool(
        name="fetch_pending_notifications",
        toolset="notification-bridge",
        schema={
            "type": "object",
            "properties": {}
        },
        handler=lambda args, **kwargs: _fetch_and_mark_notifications()
    )

    ctx.register_tool(
        name="add_notification",
        toolset="notification-bridge",
        schema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt or notification text/reminder to queue in the database."
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
