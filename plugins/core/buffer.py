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


def add_to_buffer(text: str, schedule_time: str = None) -> str:
    """
    Adds a post to the user's Buffer queue for LinkedIn.

    Args:
        text (str): Content of the LinkedIn post.
        schedule_time (str, optional): The ISO/formatted time to schedule the post.
    """
    access_token = os.environ.get("BUFFER_ACCESS_TOKEN")
    if not access_token:
        return (
            f"📝 **[MOCK SUCCESS] LinkedIn Post Queued to Buffer**:\n"
            f"- **Text Preview**: {text[:60]}...\n\n"
            f"ℹ️ *Note: BUFFER_ACCESS_TOKEN is not set. Set it in .env to publish directly to LinkedIn.*"
        )

    profiles_url = "https://api.bufferapp.com/1/profiles.json"
    updates_url = "https://api.bufferapp.com/1/updates/create.json"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        # 1. Fetch profiles to locate the LinkedIn profile ID
        if REQUESTS_AVAILABLE:
            profiles_response = requests.get(profiles_url, headers=headers, timeout=10)
            profiles_response.raise_for_status()
            profiles_data = profiles_response.json()
        else:
            req = urllib.request.Request(profiles_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                profiles_data = json.loads(resp.read().decode("utf-8"))

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

        if REQUESTS_AVAILABLE:
            update_response = requests.post(updates_url, headers=headers, data=payload, timeout=10)
            update_response.raise_for_status()
            update_data = update_response.json()
        else:
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(updates_url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                update_data = json.loads(resp.read().decode("utf-8"))

        if update_data.get("success"):
            return f"✅ **Post Queued to Buffer**! Preview: '{text[:45]}...'"
        else:
            return f"Failed to queue post: {update_data.get('message', 'Unknown error')}"

    except Exception as e:
        return f"Error communicating with Buffer API: {str(e)}"
