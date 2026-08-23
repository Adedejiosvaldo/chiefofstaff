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

    ctx.register_tool(
        name="update_todoist_task",
        toolset="todoist",
        schema={
            "type": "object",
            "description": "Reschedule or rename an existing task on Todoist by task ID or name/keyword.",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID or keyword in task name (e.g. 'chunking', 'prembly')."
                },
                "due_string": {
                    "type": "string",
                    "description": "New due date in natural language (e.g. 'tomorrow', 'next monday 10am', 'Aug 23')."
                },
                "content": {
                    "type": "string",
                    "description": "Optional new task title."
                }
            },
            "required": ["task_id"]
        },
        handler=lambda args, **kwargs: core_todoist.update_task(
            task_id_or_name=(args or {}).get("task_id") or (args or {}).get("task_name") or (args or {}).get("content") or "",
            due_string=(args or {}).get("due_string"),
            content=(args or {}).get("new_content") or (args or {}).get("content") if (args or {}).get("due_string") else None
        )
    )
