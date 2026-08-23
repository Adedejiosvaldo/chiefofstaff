#!/bin/bash
export PATH=/opt/hermes/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
if [ -f "/opt/data/.env" ]; then set -a; source /opt/data/.env 2>/dev/null || true; set +a; fi
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering LinkedIn engagement queueing..."
python3 "$CRON_DIR/queue_prompt.py" "Surface 5 high-signal LinkedIn posts for me to engage with right now based on my interests in backend dev, OCR, and fintech. Remind me why this is important."
