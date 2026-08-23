import os
import sys

# Import shared core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import buffer as core_buffer


def register(ctx):
    """Hermes plugin registration entrypoint for Buffer."""
    ctx.register_tool(
        name="buffer_queue_post",
        toolset="buffer",
        schema={
            "type": "object",
            "description": "Queues an approved post draft directly to the user's Buffer queue for LinkedIn.",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The formatted content of the LinkedIn post to publish."
                },
                "schedule_time": {
                    "type": "string",
                    "description": "Optional ISO/formatted time to schedule the post."
                }
            },
            "required": ["text"]
        },
        handler=lambda args, **kwargs: core_buffer.add_to_buffer(
            args["text"],
            args.get("schedule_time")
        )
    )
