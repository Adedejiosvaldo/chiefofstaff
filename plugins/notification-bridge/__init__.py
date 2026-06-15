import os
import sys
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


def register(ctx):
    """Hermes plugin registration entrypoint."""
    ctx.register_tool(
        name="fetch_pending_notifications",
        toolset="notification-bridge",
        schema={
            "type": "object",
            "properties": {}
        },
        handler=lambda args: _fetch_and_mark_notifications()
    )
