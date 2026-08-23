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
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The drafted LinkedIn post content to queue."
                },
                "schedule_time": {
                    "type": "string",
                    "description": "Optional scheduled ISO time."
                }
            },
            "required": ["text"]
        },
        handler=lambda args, **kwargs: core_buffer.add_to_buffer(
            text=args["text"],
            schedule_time=args.get("schedule_time")
        )
    )
