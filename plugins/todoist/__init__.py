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
            "properties": {
                "filter_query": {
                    "type": "string",
                    "description": "Todoist filter expression (defaults to 'today | overdue')."
                }
            }
        },
        handler=lambda args, **kwargs: core_todoist.fetch_todoist_tasks(args.get("filter_query", "today | overdue"))
    )

    ctx.register_tool(
        name="create_todoist_task",
        toolset="todoist",
        schema={
            "type": "object",
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
        handler=lambda args, **kwargs: core_todoist.create_task(args["content"], args.get("due_string"))
    )

    ctx.register_tool(
        name="complete_todoist_task",
        toolset="todoist",
        schema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The Todoist task ID."
                }
            },
            "required": ["task_id"]
        },
        handler=lambda args, **kwargs: core_todoist.complete_task(args["task_id"])
    )
