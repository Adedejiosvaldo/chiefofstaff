#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering blog reminder queueing..."
python3 "$CRON_DIR/queue_prompt.py" "It's time for my weekly blog post. Give me 3 topic suggestions based on my recent notes and tell me to block out time to write it today. Act as my Life Organizer."
