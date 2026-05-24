#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering daily brief queueing..."
python3 "$CRON_DIR/queue_prompt.py" "Please generate my daily brief. Include today's calendar, top 3 todos, a pre-drafted LinkedIn post, and pending approvals. Act as my Life Organizer."
