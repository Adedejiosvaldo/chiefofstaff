import os
import subprocess
import json
import urllib.request
from datetime import datetime, timedelta

GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "Adedejiosvaldo")


def get_github_remote_commits(username: str = GITHUB_USERNAME, since_hours: int = 24) -> list:
    """
    Fetches all recent commit activity for the user from GitHub's Public Events API.
    Captures commits pushed to ANY public repository today.
    """
    if not username:
        return []

    url = f"https://api.github.com/users/{username}/events"
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    commits_by_repo = {}

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"ChiefOfStaff-Agent/{username}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        # Optional GITHUB_TOKEN for higher rate limits
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            req.add_header("Authorization", f"Bearer {token}")

        with urllib.request.urlopen(req, timeout=8) as resp:
            events = json.loads(resp.read().decode("utf-8"))

        for event in events:
            if event.get("type") != "PushEvent":
                continue

            created_at_str = event.get("created_at")
            if not created_at_str:
                continue

            # Format: 2026-08-21T18:30:00Z
            event_time = datetime.strptime(created_at_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            if event_time < cutoff:
                continue

            repo_name = event.get("repo", {}).get("name", "Unknown Repo")
            payload = event.get("payload", {})
            commits = payload.get("commits", [])

            if repo_name not in commits_by_repo:
                commits_by_repo[repo_name] = []

            for commit in commits:
                msg = commit.get("message", "").split("\n")[0]
                sha = commit.get("sha", "")[:7]
                commits_by_repo[repo_name].append(f"- {msg} ({sha}) - {event_time.strftime('%I:%M %p UTC')}")

    except Exception as e:
        print(f"GitHub API events fetch warning: {e}")

    return commits_by_repo


def discover_all_local_git_repos(base_paths: list, max_depth: int = 2) -> list:
    """
    Recursively scans base development directories to discover ALL git repositories.
    """
    discovered = []
    seen = set()

    for base in base_paths:
        if not base or not os.path.exists(base):
            continue

        base_real = os.path.realpath(base)
        if os.path.exists(os.path.join(base_real, ".git")):
            if base_real not in seen:
                discovered.append(base_real)
                seen.add(base_real)
            continue

        # Walk subdirectories up to max_depth
        for root, dirs, _ in os.walk(base_real):
            # Calculate current depth relative to base
            depth = root[len(base_real):].count(os.sep)
            if depth > max_depth:
                dirs[:] = []
                continue

            if ".git" in dirs:
                if root not in seen:
                    discovered.append(root)
                    seen.add(root)
                dirs.remove(".git")

    return discovered


def get_local_git_commits(repo_paths_str: str = "", since_hours: int = 24) -> str:
    """
    Pulls ALL commits made in the last N hours across:
    1. Local repositories found on the machine.
    2. GitHub remote push events for the user.

    Args:
        repo_paths_str (str): Optional explicit list of paths.
        since_hours (int): Number of hours of history to pull (default 24).
    """
    output_lines = [f"### 🚀 Full Developer Activity Summary (Last {since_hours} Hours) ###\n"]
    commits_recorded = False

    # 1. Fetch Remote Commits from GitHub API
    github_commits = get_github_remote_commits(since_hours=since_hours)
    if github_commits:
        output_lines.append(f"🌐 **GitHub Remote Activity (https://github.com/{GITHUB_USERNAME})**:")
        for repo, commit_list in github_commits.items():
            output_lines.append(f"📦 **{repo}**")
            for c in commit_list:
                output_lines.append(f"  {c}")
            output_lines.append("")
        commits_recorded = True

    # 2. Resolve Base Search Paths for Local Repositories
    base_search_paths = []
    if repo_paths_str:
        base_search_paths = [p.strip() for p in repo_paths_str.split(",") if p.strip()]
    else:
        env_paths = os.environ.get("GIT_REPO_PATHS", "")
        if env_paths:
            base_search_paths.extend([p.strip() for p in env_paths.split(",") if p.strip()])

        # Add parent workspaces, home coding folders, and container mounts
        current_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(os.path.dirname(current_dir))
        parent_dir = os.path.dirname(repo_root)

        candidate_bases = [
            repo_root,
            parent_dir,
            os.path.expanduser("~/coding"),
            os.path.expanduser("~/code"),
            os.path.expanduser("~/projects"),
            "/opt/repos"
        ]
        base_search_paths.extend([b for b in candidate_bases if os.path.exists(b)])

    # Discover all local repos
    local_repos = discover_all_local_git_repos(base_search_paths, max_depth=2)
    since_date = (datetime.now() - timedelta(hours=since_hours)).strftime("%Y-%m-%d %H:%M:%S")

    local_commits_output = []
    for repo_path in local_repos:
        repo_name = os.path.basename(os.path.normpath(repo_path))
        try:
            cmd = [
                "git", "log",
                f"--since={since_date}",
                "--pretty=format:  - %s (%h) - %ad",
                "--date=relative"
            ]
            output = subprocess.check_output(cmd, cwd=repo_path, stderr=subprocess.DEVNULL, timeout=4).decode("utf-8").strip()
            if output:
                local_commits_output.append(f"📁 **Local Repo: {repo_name}** ({repo_path})")
                local_commits_output.append(output)
                local_commits_output.append("")
                commits_recorded = True
        except Exception:
            continue

    if local_commits_output:
        output_lines.append("💻 **Local Workstation Commits**:")
        output_lines.extend(local_commits_output)

    if not commits_recorded:
        output_lines.append("- No commits logged locally or on GitHub in the last 24 hours.")

    return "\n".join(output_lines)
