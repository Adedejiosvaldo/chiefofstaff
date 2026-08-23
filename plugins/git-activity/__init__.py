import os
import sys

# Import shared core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import git_activity as core_git


def register(ctx):
    """Hermes plugin registration entrypoint for Git Activity."""
    ctx.register_tool(
        name="analyze_local_git_activity",
        toolset="git-activity",
        schema={
            "type": "object",
            "description": "Pulls recent git commit history and push events across local repositories and GitHub for the user.",
            "properties": {
                "repo_paths_str": {
                    "type": "string",
                    "description": "Comma-separated absolute paths to git repositories. If empty, auto-discovers repos and checks GitHub."
                },
                "since_hours": {
                    "type": "integer",
                    "description": "Number of hours of history to pull (default 24)."
                }
            }
        },
        handler=lambda args, **kwargs: core_git.get_local_git_commits(
            (args or {}).get("repo_paths_str", ""),
            (args or {}).get("since_hours", 24)
        )
    )
