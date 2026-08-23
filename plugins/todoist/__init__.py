import os
import sys

# Import shared core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import todoist as core_todoist


def register(ctx):
    """Hermes plugin registration entrypoint for Todoist."""
    ctx.register_tool(
        name="get_todoist_tasks",
        toolset="todoist",
        schema={
            "type": "object",
            "description": "Fetch active, today, and overdue tasks from Todoist task board.",
            "properties": {
                "filter_query": {
                    "type": "string",
                    "description": "Todoist filter expression (defaults to 'today | overdue')."
                }
            }
        },
        handler=lambda args, **kwargs: core_todoist.fetch_todoist_tasks((args or {}).get("filter_query", "today | overdue"))
    )

    ctx.register_tool(
        name="create_todoist_task",
        toolset="todoist",
        schema={
            "type": "object",
            "description": "Create a new task on the Todoist task board.",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The task name/content."
                },
                "due_string": {
                    "type": "string",
                    "description": "Natural date text e.g., 'today', 'monday 4pm'."
                }
            },
            "required": ["content"]
        },
        handler=lambda args, **kwargs: core_todoist.create_task((args or {}).get("content", ""), (args or {}).get("due_string"))
    )

    ctx.register_tool(
        name="complete_todoist_task",
        toolset="todoist",
        schema={
            "type": "object",
            "description": "Mark a Todoist task as completed by task ID or matching task name/keywords.",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The Todoist task ID or task title/keyword (e.g. 'livestreaming', 'prembly', '6hJRfFhWP3hVFcR7')."
                }
            },
            "required": ["task_id"]
        },
        handler=lambda args, **kwargs: core_todoist.complete_task((args or {}).get("task_id") or (args or {}).get("task_name") or (args or {}).get("content") or "")
    )
