#!/bin/bash
export PATH=/opt/hermes/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
if [ -f "/opt/data/.env" ]; then set -a; source /opt/data/.env 2>/dev/null || true; set +a; fi
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering global opportunity crawling..."

# 1. Run crawler script in background to populate SQLite opportunity cache
python3 -c "
import sys, os
current_dir = os.path.dirname(os.path.abspath('$CRON_DIR/opportunity_aggregator.sh'))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../plugins')))
sys.path.insert(0, os.path.expanduser('~/.hermes/plugins'))
if os.path.exists('/opt/data/plugins'):
    sys.path.insert(0, '/opt/data/plugins')

try:
    from core import opportunity
    res = opportunity.trigger_crawlers()
    print(res)
except Exception as e:
    print('Error running opportunity crawler:', e)
"

# 2. Queue prompt to alert the agent to pull cached matches and present them
python3 "$CRON_DIR/queue_prompt.py" "A background crawl has completed. Please pull unread opportunities from your radar using the pull_radar_opportunities tool and present them in a concise briefing. Act as my Global Opportunity Radar."
