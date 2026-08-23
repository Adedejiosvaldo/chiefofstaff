#!/bin/bash
export PATH=/opt/hermes/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
if [ -f "/opt/data/.env" ]; then set -a; source /opt/data/.env 2>/dev/null || true; set +a; fi
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Queuing weekly routine self-analysis..."

python3 -c "
import sys, os
current_dir = os.path.dirname(os.path.abspath('$CRON_DIR/weekly_routine_analysis.sh'))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../plugins')))
sys.path.insert(0, os.path.expanduser('~/.hermes/plugins'))
if os.path.exists('/opt/data/plugins'):
    sys.path.insert(0, '/opt/data/plugins')

try:
    from core import db
    prompt = (
        'It is Sunday 9:00 PM Lagos time. Please execute a weekly routine analysis. '
        'Check recent telemetry logs, evaluate schedule compliance, summarize '
        'how our partnership has grown, and let me know if we should adapt our '
        'daily briefing or nudge times. Act as my Adaptive Partner.'
    )
    db.add_notification(prompt)
    print('Weekly routine analysis successfully queued in SQLite!')
except Exception as e:
    print('Error inserting routine analysis alert:', e)
"
