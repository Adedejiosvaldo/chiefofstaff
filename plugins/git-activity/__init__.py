import os
import subprocess
from datetime import datetime, timedelta


def _get_git_user_identity(repo_path: str) -> tuple:
    """Attempts to discover local git user name and email from config."""
    try:
        name = subprocess.check_output(
            ["git", "config", "user.name"],
            cwd=repo_path,
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        email = subprocess.check_output(
            ["git", "config", "user.email"],
            cwd=repo_path,
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        return name, email
    except Exception:
        return "", ""


def _get_local_git_commits(repo_paths_str: str = "", since_hours: int = 24) -> str:
    """
    Scans a list of local repository directories and summarizes git commits made.

    Args:
        repo_paths_str (str): Comma-separated absolute folder paths. If empty, checks environment variables.
        since_hours (int): Number of hours of history to pull (default 24).

    Returns:
        str: A formatted summary of git commits grouped by repository.
    """
    # 1. Resolve repository paths
    paths = []
    if repo_paths_str:
        paths = [p.strip() for p in repo_paths_str.split(",") if p.strip()]
    else:
        env_paths = os.environ.get("GIT_REPO_PATHS", "")
        if env_paths:
            paths = [p.strip() for p in env_paths.split(",") if p.strip()]
        else:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            parent_parent = os.path.dirname(parent_dir)
            if os.path.exists(os.path.join(parent_parent, "zgic-staffclockin")):
                paths = [os.path.join(parent_parent, "zgic-staffclockin")]
            else:
                paths = [parent_dir]

    if not paths:
        return "Error: No git repository paths configured or specified."

    since_date = (datetime.now() - timedelta(hours=since_hours)).strftime("%Y-%m-%d %H:%M:%S")
    summary_output = [f"### Git Activity Summary (Last {since_hours} Hours) ###\n"]

    for path in paths:
        if not os.path.exists(path):
            summary_output.append(f"⚠️ Directory not found: {path}\n")
            continue
        if not os.path.exists(os.path.join(path, ".git")):
            summary_output.append(f"⚠️ Not a Git repository: {path}\n")
            continue

        repo_name = os.path.basename(os.path.normpath(path))
        summary_output.append(f"📁 **Repository: {repo_name}** ({path})")

        name, email = _get_git_user_identity(path)
        author_filter = email if email else (name if name else "")

        try:
            cmd = [
                "git", "log",
                f"--since={since_date}",
                "--pretty=format:- %s (%h) - %ad",
                "--date=relative"
            ]
            if author_filter:
                cmd.append(f"--author={author_filter}")

            output = subprocess.check_output(
                cmd,
                cwd=path,
                stderr=subprocess.STDOUT
            ).decode("utf-8").strip()

            if output:
                summary_output.append(output)
            else:
                summary_output.append("- No commits logged by you in this window.")
        except subprocess.CalledProcessError as e:
            summary_output.append(f"- Failed to read commits: {e.output.decode('utf-8').strip()}")
        except Exception as e:
            summary_output.append(f"- An error occurred: {str(e)}")
        summary_output.append("")

    return "\n".join(summary_output)


def register(ctx):
    """Hermes plugin registration entrypoint."""
    ctx.register_tool(
        name="analyze_local_git_activity",
        toolset="git-activity",
        schema={
            "type": "object",
            "properties": {
                "repo_paths_str": {
                    "type": "string",
                    "description": "Comma-separated absolute paths to git repositories. If empty, uses GIT_REPO_PATHS env var."
                },
                "since_hours": {
                    "type": "integer",
                    "description": "Number of hours of history to pull (default 24)."
                }
            }
        },
        handler=lambda args: _get_local_git_commits(
            args.get("repo_paths_str", ""),
            args.get("since_hours", 24)
        )
    )
