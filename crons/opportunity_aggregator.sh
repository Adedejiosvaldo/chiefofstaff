#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
CRON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Triggering global opportunity crawling..."

# 1. Run crawler script in background to populate SQLite opportunity cache
python3 -c "
import sys, os
current_dir = os.path.dirname(os.path.abspath('$CRON_DIR/opportunity_aggregator.sh'))
sys.path.append(os.path.abspath(os.path.join(current_dir, '../plugins')))
sys.path.append(os.path.expanduser('~/.hermes/plugins'))
if os.path.exists('/opt/data/plugins'):
    sys.path.append('/opt/data/plugins')

try:
    import opportunity_plugin
    res = opportunity_plugin.trigger_crawlers()
    print(res)
except Exception as e:
    print('Error running opportunity crawler:', e)
"

# 2. Queue prompt to alert the agent to pull cached matches and present them
python3 "$CRON_DIR/queue_prompt.py" "A background crawl has completed. Please pull unread opportunities from your radar using the pull_radar_opportunities tool and present them to me in a concise briefing. Act as my Global Opportunity Radar."
