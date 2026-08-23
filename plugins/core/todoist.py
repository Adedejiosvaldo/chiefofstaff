import os
import json
import urllib.request
import urllib.parse
import urllib.error

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def get_todoist_headers() -> dict:
    """Returns authorization headers for Todoist API v1."""
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_mock_tasks() -> str:
    """Generates a clean mock list of accountability tasks for the developer profile."""
    tasks = [
        "📋 **[MOCK] Todoist Active Tasks**:",
        "1. **[task-101]** Review composite score trust check in zgic-staffclockin enrollment",
        "2. **[task-102]** Write weekly blog post on Distributed System Concurrency Pitfalls",
        "3. **[task-103]** Perform 30 minutes of deep developer networking on LinkedIn",
        "4. **[task-104]** Research advanced vector indexing strategies for massive RAG databases",
        "\nℹ️ *Todoist API token missing. Set TODOIST_API_TOKEN in your environment to sync your real task board.*"
    ]
    return "\n".join(tasks)


def fetch_todoist_tasks(filter_query: str = "today | overdue") -> str:
    """
    Fetches open tasks from the official Todoist API v1 matching a query filter.

    Args:
        filter_query (str): Todoist filter expression (defaults to 'today | overdue').
    """
    headers = get_todoist_headers()
    if not headers:
        return get_mock_tasks()

    url = "https://api.todoist.com/api/v1/tasks"
    params = {}
    if filter_query:
        params["filter"] = filter_query

    try:
        if REQUESTS_AVAILABLE:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        else:
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}" if query_string else url
            req = urllib.request.Request(full_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

        tasks = data.get("results", data) if isinstance(data, dict) else data

        if not tasks:
            return "✅ **Todoist Board**: No active or overdue tasks scheduled! Excellent work."

        output = ["📋 **Todoist Active Tasks**:\n"]
        for idx, task in enumerate(tasks, 1):
            due = task.get("due") or {}
            due_str = due.get("string", due.get("date", "No due date"))
            content = task.get("content", "Untitled Task")
            task_id = task.get("id")

            output.append(f"{idx}. **[{task_id}]** {content}  ·  *Due: {due_str}*")

        return "\n".join(output)

    except Exception as e:
        return f"Error communicating with Todoist API: {str(e)}\n\n" + get_mock_tasks()


def create_task(content: str, due_string: str = None) -> str:
    """
    Creates a new task in Todoist API v1.

    Args:
        content (str): The text of the task.
        due_string (str, optional): Natural date text e.g., 'today', 'friday at 4pm'.
    """
    headers = get_todoist_headers()
    if not headers:
        return (
            f"📝 **[MOCK SUCCESS] Created Todoist Task**:\n"
            f"- **Content**: {content}\n"
            f"- **Due Date**: {due_string if due_string else 'None'}\n\n"
            f"ℹ️ *Note: TODOIST_API_TOKEN is missing. This mock task has been recorded.*"
        )

    url = "https://api.todoist.com/api/v1/tasks"
    payload = {"content": content}
    if due_string:
        payload["due_string"] = due_string

    try:
        if REQUESTS_AVAILABLE:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            task = response.json()
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                task = json.loads(resp.read().decode("utf-8"))

        return f"✅ **Todoist Task Created**!\n- **Content**: {task.get('content')}\n- **ID**: {task.get('id')}"
    except Exception as e:
        return f"Error creating Todoist task: {str(e)}"


def complete_task(task_id: str) -> str:
    """
    Marks a Todoist task as completed via API v1.

    Args:
        task_id (str): The Todoist alphanumeric ID.
    """
    headers = get_todoist_headers()
    if not headers:
        return f"✅ **[MOCK SUCCESS] Completed Todoist Task**: Marked task ID **'{task_id}'** as completed."

    url = f"https://api.todoist.com/api/v1/tasks/{task_id}/close"

    try:
        if REQUESTS_AVAILABLE:
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
        else:
            req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        return f"✅ **Todoist Task Completed**! Successfully checked off task {task_id}."
    except Exception as e:
        return f"Error completing Todoist task: {str(e)}"
