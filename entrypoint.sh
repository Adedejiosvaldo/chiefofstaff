#!/bin/bash
set -e

echo "=========================================================="
echo "Starting Personal Chief of Staff Container Setup..."
echo "=========================================================="

# 1. Sync custom skills, plugins, and crons to persistent mount (/opt/data/)
mkdir -p /opt/data/skills
mkdir -p /opt/data/plugins
mkdir -p /opt/data/crons

echo "Syncing plugins, skills, and crons to persistent volume..."
cp -r /opt/app/skills/* /opt/data/skills/ 2>/dev/null || true
cp -r /opt/app/plugins/* /opt/data/plugins/ 2>/dev/null || true
cp -r /opt/app/crons/* /opt/data/crons/ 2>/dev/null || true

# 2. Setup .env environment file inside mount if not already present
if [ ! -f "/opt/data/.env" ]; then
    if [ -f "/opt/data/.env.example" ]; then
        cp /opt/data/.env.example /opt/data/.env
    elif [ -f "/opt/app/.env.example" ]; then
        cp /opt/app/.env.example /opt/data/.env
    fi
    echo "ℹ️ Created /opt/data/.env. Please configure your API tokens on the host."
fi

# 2b. Setup config.yaml inside mount if not already present to explicitly enable WhatsApp platform and configure default model
if [ ! -f "/opt/data/config.yaml" ]; then
    cat << 'EOF' > /opt/data/config.yaml
platforms:
  whatsapp:
    enabled: true

model:
  provider: openrouter
  default: "anthropic/claude-3.5-sonnet"
EOF
    echo "ℹ️ Created default /opt/data/config.yaml with WhatsApp platform and OpenRouter model enabled."
fi


# 3. Automatically register the crontab inside the container
echo "Installing cron schedules..."
CRON_DIR="/opt/data/crons"
TEMP_CRON=$(mktemp)
crontab -l > "$TEMP_CRON" 2>/dev/null || true
sed -i '/opt\/data\/crons/d' "$TEMP_CRON" || true

# Daily brief at 7:00 AM every weekday (Monday to Friday)
echo "0 7 * * 1-5 $CRON_DIR/daily_brief.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# Blog reminder at 9:00 AM on Monday and Friday
echo "0 9 * * 1,5 $CRON_DIR/blog_reminder.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# Blog follow-up at 4:00 PM on Monday and Friday
echo "0 16 * * 1,5 $CRON_DIR/blog_followup.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# LinkedIn engagement at 8:00 AM and 5:00 PM every weekday
echo "0 8 * * 1-5 $CRON_DIR/linkedin_engagement.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"
echo "0 17 * * 1-5 $CRON_DIR/linkedin_engagement.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# Weekly content batch at 6:00 PM on Sunday
echo "0 18 * * 0 $CRON_DIR/weekly_content_batch.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# Opportunity Aggregator at 12:00 PM every weekday (Monday to Friday)
echo "0 12 * * 1-5 $CRON_DIR/opportunity_aggregator.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# Weekly routine self-training analysis at 9:00 PM on Sunday
echo "0 21 * * 0 $CRON_DIR/weekly_routine_analysis.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# Proactive accountability nudge coach daily at 5:00 PM
echo "0 17 * * * $CRON_DIR/nudge_coach.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

crontab "$TEMP_CRON"
rm "$TEMP_CRON"

# 4. Boot up background cron service
echo "Launching cron background daemon..."
service cron start || /usr/sbin/cron

# 5. Locate the hermes executable dynamically
echo "Locating Hermes executable..."
if [ -f "/opt/hermes/.venv/bin/hermes" ]; then
    HERMES_BIN="/opt/hermes/.venv/bin/hermes"
    echo "Found Hermes in virtualenv: $HERMES_BIN"
elif command -v hermes &> /dev/null; then
    HERMES_BIN="hermes"
    echo "Found Hermes in global PATH: $HERMES_BIN"
else
    HERMES_BIN=$(find /opt/ /usr/ -name hermes -type f -executable -print -quit 2>/dev/null || echo "hermes")
    echo "Located Hermes at: $HERMES_BIN"
fi

# 6. Allow running gateway as root to ensure perfect file-permission symmetry with background cron daemon
export HERMES_ALLOW_ROOT_GATEWAY=1

# 7. Start the Hermes Gateway. If it exits (e.g. because it's not paired yet), keep the container alive so you can pair.
echo "=========================================================="
echo "Starting Hermes Gateway..."
echo "=========================================================="
"$HERMES_BIN" gateway run || true

echo "=========================================================="
echo "⚠️ Gateway stopped or is waiting for WhatsApp pairing."
echo "Keeping the container alive so you can run the pairing command:"
echo "👉 docker exec -it chief-of-staff-agent /opt/hermes/.venv/bin/hermes whatsapp"
echo "=========================================================="
tail -f /dev/null

