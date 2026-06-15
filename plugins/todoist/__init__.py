import os
import requests
import json


def _get_todoist_headers() -> dict:
    """Returns authorization headers for the Todoist API if token is configured."""
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def _get_mock_tasks() -> str:
    """Generates a clean mock list of accountability tasks for Backend/AI developer profile."""
    tasks = [
        "📋 **[MOCK] Todoist Accountability Tasks**:",
        "1. **[mock-task-101]** Write weekly Monday blog post on Distributed System Concurrency Pitfalls",
        "2. **[mock-task-102]** Perform 30 minutes of deep LinkedIn developer networking",
        "3. **[mock-task-103]** Optimize composite score trust check in zgic-staffclockin enrollment",
        "4. **[mock-task-104]** Research advanced vector indexing strategies for massive RAG databases",
        "\nℹ️ *Todoist API token missing. To connect your actual task boards, add TODOIST_API_TOKEN to your .env file*"
    ]
    return "\n".join(tasks)


def _fetch_todoist_tasks(filter_query: str = "today | overdue") -> str:
    """
    Fetches open tasks from Todoist matching a query filter.

    Args:
        filter_query (str): Todoist filter expression (defaults to 'today | overdue').
    """
    headers = _get_todoist_headers()
    if not headers:
        return _get_mock_tasks()

    url = "https://api.todoist.com/api/v1/tasks"
    params = {"filter": filter_query}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict):
            tasks = data.get("tasks") or data.get("items") or data.get("results") or []
        else:
            tasks = data

        if not tasks:
            return "✅ **Todoist Board**: No active or overdue tasks scheduled! Excellent work."

        output = ["📋 **Todoist Active Tasks**:\n"]
        for idx, task in enumerate(tasks, 1):
            due = task.get("due", {})
            due_str = due.get("string", "No due date")
            project = task.get("project_id", "Inbox")

            output.append(
                f"{idx}. **[{task.get('id')}]** {task.get('content')}\n"
                f"   - *Due*: {due_str} | *Project/Area*: {project}"
            )
        return "\n".join(output)

    except requests.exceptions.RequestException as e:
        return f"Error communicating with Todoist API: {str(e)}\n\n" + _get_mock_tasks()


def _create_task(content: str, due_string: str = None) -> str:
    """
    Creates a new task in Todoist.

    Args:
        content (str): The text of the task.
        due_string (str, optional): Todoist natural date text e.g., 'today', 'next monday at 4pm'.
    """
    headers = _get_todoist_headers()
    if not headers:
        return (
            f"📝 **[MOCK SUCCESS] Created Todoist Task**:\n"
            f"- **Content**: {content}\n"
            f"- **Due Date**: {due_string if due_string else 'None'}\n\n"
            f"ℹ️ *Note: TODOIST_API_TOKEN is missing. This mock task has been successfully logged.*"
        )

    url = "https://api.todoist.com/api/v1/tasks"
    payload = {"content": content}
    if due_string:
        payload["due_string"] = due_string

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        task = data.get("task") or data.get("item") or data if isinstance(data, dict) else {}
        return f"✅ **Todoist Task Created**!\n- **Content**: {task.get('content')}\n- **ID**: {task.get('id')}"
    except requests.exceptions.RequestException as e:
        return f"Error creating Todoist task: {str(e)}"


def _complete_task(task_id: str) -> str:
    """
    Marks a Todoist task as completed.

    Args:
        task_id (str): The Todoist alphanumeric ID.
    """
    headers = _get_todoist_headers()
    if not headers:
        return (
            f"✅ **[MOCK SUCCESS] Completed Todoist Task**:\n"
            f"- Marked task ID **'{task_id}'** as completed."
        )

    url = f"https://api.todoist.com/api/v1/tasks/{task_id}/close"

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return f"✅ **Todoist Task Completed**! Successfully checked off task {task_id}."
    except requests.exceptions.RequestException as e:
        return f"Error completing Todoist task: {str(e)}"


def register(ctx):
    """Hermes plugin registration entrypoint."""
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
        handler=lambda args, **kwargs: _fetch_todoist_tasks(args.get("filter_query", "today | overdue"))
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
        handler=lambda args, **kwargs: _create_task(args["content"], args.get("due_string"))
    )
    ctx.register_tool(
        name="complete_todoist_task",
        toolset="todoist",
        schema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The Todoist alphanumeric task ID."
                }
            },
            "required": ["task_id"]
        },
        handler=lambda args, **kwargs: _complete_task(args["task_id"])
    )
