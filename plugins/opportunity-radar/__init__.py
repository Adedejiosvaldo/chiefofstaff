import os
import sys

# Import shared core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import opportunity as core_opportunity


def register(ctx):
    """Hermes plugin registration entrypoint for Opportunity Radar."""
    ctx.register_tool(
        name="run_opportunity_crawler",
        toolset="opportunity-radar",
        schema={
            "type": "object",
            "description": "Crawls remote sources for international DevOps, SRE, and Cloud jobs offering relocation / visa sponsorship.",
            "properties": {}
        },
        handler=lambda args, **kwargs: core_opportunity.trigger_crawlers()
    )

    ctx.register_tool(
        name="pull_radar_opportunities",
        toolset="opportunity-radar",
        schema={
            "type": "object",
            "description": "Fetches cached unread international DevOps jobs and relocation opportunities from SQLite.",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of opportunities to return (default 5)."
                }
            }
        },
        handler=lambda args, **kwargs: core_opportunity.pull_cached_opportunities(args.get("limit", 5))
    )
