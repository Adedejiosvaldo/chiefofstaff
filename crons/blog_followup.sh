#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering blog follow-up queueing..."
python3 "$CRON_DIR/queue_prompt.py" "Follow up with me on the blog post I was supposed to write today. Ask me if it's done. If not, push me to do it now. Act as my Life Organizer."
