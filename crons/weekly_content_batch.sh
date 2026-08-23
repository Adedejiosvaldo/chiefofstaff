#!/bin/bash
export PATH=/opt/hermes/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
if [ -f "/opt/data/.env" ]; then set -a; source /opt/data/.env 2>/dev/null || true; set +a; fi
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering weekly content batch queueing..."
python3 "$CRON_DIR/queue_prompt.py" "Draft 3 LinkedIn posts for the upcoming week based on my recent notes and trending topics. Present them for approval."
