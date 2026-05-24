#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Queuing weekly routine self-analysis..."

# Execute a Python one-liner to insert the notification securely into the SQLite database
python3 -c "
import sys, os
current_dir = os.path.dirname(os.path.abspath('$CRON_DIR/weekly_routine_analysis.sh'))
sys.path.append(os.path.abspath(os.path.join(current_dir, '../plugins')))
sys.path.append(os.path.expanduser('~/.hermes/plugins'))
if os.path.exists('/opt/data/plugins'):
    sys.path.append('/opt/data/plugins')

try:
    import chief_of_staff_db
    prompt = (
        'It is Sunday 9:00 PM Lagos time. Please execute a weekly routine analysis. '
        'Check recent telemetry logs, evaluate my schedule compliance, summarize '
        'how our partnership has grown, and let me know if we should adapt our '
        'daily briefing or nudge times. Act as my Adaptive Partner.'
    )
    chief_of_staff_db.add_notification(prompt)
    print('Weekly routine analysis successfully queued in SQLite!')
except Exception as e:
    print('Error inserting routine analysis alert:', e)
"
