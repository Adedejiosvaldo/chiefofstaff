import os
import requests
import json


def _add_to_buffer(text: str, schedule_time: str = None) -> str:
    """
    Adds a post to the user's Buffer queue for LinkedIn.

    Args:
        text (str): The content of the LinkedIn post.
        schedule_time (str, optional): The time to schedule the post. If None, it adds to the next available slot.

    Returns:
        str: A success or error message to return to the user.
    """
    access_token = os.environ.get("BUFFER_ACCESS_TOKEN")
    if not access_token:
        return "Error: BUFFER_ACCESS_TOKEN environment variable is not set."

    profiles_url = "https://api.bufferapp.com/1/profiles.json"
    updates_url = "https://api.bufferapp.com/1/updates/create.json"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        # 1. Fetch profiles to find the LinkedIn profile ID
        profiles_response = requests.get(profiles_url, headers=headers)
        profiles_response.raise_for_status()
        profiles_data = profiles_response.json()

        linkedin_profile_id = None
        for profile in profiles_data:
            if profile.get("service") == "linkedin":
                linkedin_profile_id = profile.get("id")
                break

        if not linkedin_profile_id:
            return "Error: Could not find a linked LinkedIn profile in your Buffer account."

        # 2. POST the update
        payload = {
            "text": text,
            "profile_ids[]": linkedin_profile_id
        }

        if schedule_time:
            payload["scheduled_at"] = schedule_time

        update_response = requests.post(updates_url, headers=headers, data=payload)
        update_response.raise_for_status()
        update_data = update_response.json()

        if update_data.get("success"):
            return f"Successfully queued post to Buffer. Content preview: '{text[:30]}...'"
        else:
            return f"Failed to queue post: {update_data.get('message', 'Unknown error')}"

    except requests.exceptions.RequestException as e:
        return f"Error communicating with Buffer API: {str(e)}"
    except json.JSONDecodeError:
        return "Error parsing response from Buffer API."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


def register(ctx):
    """Hermes plugin registration entrypoint."""
    ctx.register_tool(
        name="buffer_queue_post",
        schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The content of the LinkedIn post to queue."
                },
                "schedule_time": {
                    "type": "string",
                    "description": "Optional ISO datetime to schedule the post. If omitted, adds to next available Buffer slot."
                }
            },
            "required": ["text"]
        },
        handler=lambda args: _add_to_buffer(args["text"], args.get("schedule_time"))
    )
