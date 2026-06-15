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
cp -r /opt/app/crons/* /opt/data/crons/ 2>/dev/null || true

# Sync directory-based plugins (each is a folder with plugin.yaml + __init__.py)
for plugin_dir in /opt/app/plugins/*/; do
    if [ -f "${plugin_dir}plugin.yaml" ]; then
        plugin_name=$(basename "$plugin_dir")
        mkdir -p "/opt/data/plugins/${plugin_name}"
        cp -r "${plugin_dir}"* "/opt/data/plugins/${plugin_name}/" 2>/dev/null || true
        echo "  ✓ Synced plugin: ${plugin_name}"
    fi
done

# Sync shared Python modules (e.g., chief_of_staff_db.py) that plugins import
for shared_file in /opt/app/plugins/*.py; do
    if [ -f "$shared_file" ]; then
        cp "$shared_file" /opt/data/plugins/ 2>/dev/null || true
        echo "  ✓ Synced shared module: $(basename $shared_file)"
    fi
done

# 2. Setup .env environment file inside mount if not already present
if [ ! -f "/opt/data/.env" ]; then
    if [ -f "/opt/data/.env.example" ]; then
        cp /opt/data/.env.example /opt/data/.env
    elif [ -f "/opt/app/.env.example" ]; then
        cp /opt/app/.env.example /opt/data/.env
    fi
    echo "ℹ️ Created /opt/data/.env. Please configure your API tokens on the host."
fi

# 2b. Safely initialize and configure config.yaml using Hermes PyYAML to enable whatsapp and the 6 custom plugins
echo "Configuring config.yaml and enabling custom plugins..."
/opt/hermes/.venv/bin/python -c '
import os, yaml
path = "/opt/data/config.yaml"
config = {}
if os.path.exists(path):
    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"  ⚠️ Warning: could not parse existing config.yaml: {e}")

# Platforms
if "platforms" not in config: config["platforms"] = {}
if "whatsapp" not in config["platforms"]: config["platforms"]["whatsapp"] = {}
config["platforms"]["whatsapp"]["enabled"] = True
config["platforms"]["whatsapp"]["group_policy"] = "disabled"

# Model
if "model" not in config:
    config["model"] = {"provider": "openrouter", "default": "anthropic/claude-3-5-sonnet"}
else:
    # Migrate legacy model syntax if present
    if config.get("model", {}).get("default") == "anthropic/claude-3.5-sonnet":
        config["model"]["default"] = "anthropic/claude-3-5-sonnet"

# Plugins
if "plugins" not in config: config["plugins"] = {}
if "enabled" not in config["plugins"] or not isinstance(config["plugins"]["enabled"], list):
    config["plugins"]["enabled"] = []

required = ["todoist", "buffer", "google-calendar", "git-activity", "opportunity-radar", "notification-bridge", "oya-gamification"]
for p in required:
    if p not in config["plugins"]["enabled"]:
        config["plugins"]["enabled"].append(p)

# Cron Wrap Response (Set to False for premium, user-friendly clean text notifications without headers/footers)
if "cron" not in config: config["cron"] = {}
config["cron"]["wrap_response"] = False

with open(path, "w") as f:
    yaml.safe_dump(config, f, default_flow_style=False)
print("  ✓ config.yaml configured. Enabled plugins: " + ", ".join(config["plugins"]["enabled"]))
'



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

# 7. Enable directory-based plugin discovery from /opt/data/plugins/
export HERMES_ENABLE_PROJECT_PLUGINS=true

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

