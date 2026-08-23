#!/bin/bash
export PATH=/opt/hermes/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
if [ -f "/opt/data/.env" ]; then set -a; source /opt/data/.env 2>/dev/null || true; set +a; fi
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering blog follow-up queueing..."
python3 "$CRON_DIR/queue_prompt.py" "Follow up with me on the blog post I was supposed to write today. Ask me if it's done. If not, push me to do it now. Act as my Life Organizer."
