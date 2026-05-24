#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
echo "Triggering weekly content batch queueing..."
python3 "$HOME/.hermes/crons/queue_prompt.py" "Draft 3 LinkedIn posts for the upcoming week based on my recent notes and trending topics. Present them for approval."
