#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
echo "Triggering proactive accountability nudge coach..."
python3 "$HOME/.hermes/crons/nudge_coach.py"
