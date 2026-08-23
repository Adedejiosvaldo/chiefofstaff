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

# Sync core module directory
if [ -d "/opt/app/plugins/core" ]; then
    mkdir -p /opt/data/plugins/core
    cp -r /opt/app/plugins/core/* /opt/data/plugins/core/ 2>/dev/null || true
    echo "  ✓ Synced core library module: plugins/core"
fi

# Sync directory-based plugins (each is a folder with plugin.yaml + __init__.py)
for plugin_dir in /opt/app/plugins/*/; do
    if [ -f "${plugin_dir}plugin.yaml" ]; then
        plugin_name=$(basename "$plugin_dir")
        mkdir -p "/opt/data/plugins/${plugin_name}"
        cp -r "${plugin_dir}"* "/opt/data/plugins/${plugin_name}/" 2>/dev/null || true
        echo "  ✓ Synced plugin: ${plugin_name}"
    fi
done

# Sync shared Python modules (e.g., chief_of_staff_db.py)
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

# 2b. Safely initialize and configure config.yaml using Hermes PyYAML
echo "Configuring config.yaml and enabling custom plugins..."
python3 -c '
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

# Model routing: ALWAYS align model with environment variables
chosen_model = os.environ.get("LLM_MODEL_WHATSAPP") or "deepseek/deepseek-chat"
config["model"] = {
    "provider": "openrouter",
    "default": chosen_model
}

# Auxiliary model routing
if "auxiliary" not in config: config["auxiliary"] = {}
config["auxiliary"]["openrouter_model"] = os.environ.get("LLM_MODEL_CRONS") or "deepseek/deepseek-chat"

# Plugins
if "plugins" not in config: config["plugins"] = {}
if "enabled" not in config["plugins"] or not isinstance(config["plugins"]["enabled"], list):
    config["plugins"]["enabled"] = []

required = ["todoist", "buffer", "google-calendar", "git-activity", "opportunity-radar", "notification-bridge", "oya-gamification"]
for p in required:
    if p not in config["plugins"]["enabled"]:
        config["plugins"]["enabled"].append(p)

# Cron configuration
if "cron" not in config: config["cron"] = {}
config["cron"]["enabled"] = True
config["cron"]["allow_agent_scheduling"] = True
config["cron"]["wrap_response"] = False

# Display
if "display" not in config: config["display"] = {}
config["display"]["tool_progress"] = "off"

with open(path, "w") as f:
    yaml.safe_dump(config, f, default_flow_style=False)
print("  ✓ config.yaml configured. Active Model: " + chosen_model + " | Enabled plugins: " + ", ".join(config["plugins"]["enabled"]))
'

# 2c. Sync config, skills, plugins, and SOUL.md to ~/.hermes/
echo "Syncing configurations, skills, and plugins to ~/.hermes/..."
mkdir -p ~/.hermes/skills ~/.hermes/plugins ~/.hermes/crons
rm -f /opt/data/skills/*.md 2>/dev/null || true
rm -f ~/.hermes/skills/*.md 2>/dev/null || true
cp -r /opt/data/skills/* ~/.hermes/skills/ 2>/dev/null || true
cp -r /opt/data/plugins/* ~/.hermes/plugins/ 2>/dev/null || true
cp -r /opt/data/crons/* ~/.hermes/crons/ 2>/dev/null || true
if [ -f "/opt/data/config.yaml" ]; then cp /opt/data/config.yaml ~/.hermes/config.yaml; fi
if [ -f "/opt/app/SOUL.md" ]; then
    cp /opt/app/SOUL.md /opt/data/SOUL.md
    cp /opt/app/SOUL.md ~/.hermes/SOUL.md
elif [ -f "/opt/data/SOUL.md" ]; then
    cp /opt/data/SOUL.md ~/.hermes/SOUL.md
fi

# 3. Export environment variables to /etc/environment for background cron jobs
printenv | grep -E '^(OPENROUTER|DEEPSEEK|ANTHROPIC|GROQ|TODOIST|BUFFER|GITHUB|GIT_REPO|TZ|WHATSAPP|HERMES)' > /etc/environment 2>/dev/null || true

# 4. Register the crontab inside container with virtualenv PATH and PYTHONPATH
echo "Installing cron schedules..."
CRON_DIR="/opt/data/crons"
TEMP_CRON=$(mktemp)
crontab -l > "$TEMP_CRON" 2>/dev/null || true
sed -i '/opt\/data\/crons/d' "$TEMP_CRON" || true
sed -i '/PATH=/d' "$TEMP_CRON" || true
sed -i '/PYTHONPATH=/d' "$TEMP_CRON" || true

# Set environment header at top of crontab
echo "PATH=/opt/hermes/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" >> "$TEMP_CRON"
echo "PYTHONPATH=/opt/data/plugins:/opt/data/plugins/core" >> "$TEMP_CRON"

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

# Weekly routine analysis at 9:00 PM on Sunday
echo "0 21 * * 0 $CRON_DIR/weekly_routine_analysis.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

# Proactive accountability nudge coach daily at 5:00 PM
echo "0 17 * * * $CRON_DIR/nudge_coach.sh >> /opt/data/cron.log 2>&1" >> "$TEMP_CRON"

crontab "$TEMP_CRON"
rm "$TEMP_CRON"

# 5. Boot background cron service
echo "Launching cron background daemon..."
service cron start || /usr/sbin/cron

# 6. Locate hermes binary
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

export HERMES_ALLOW_ROOT_GATEWAY=1
export HERMES_ENABLE_PROJECT_PLUGINS=true

# 7. Start Hermes Gateway
echo "=========================================================="
echo "Starting Hermes Gateway with DeepSeek-V3 Engine..."
echo "=========================================================="
"$HERMES_BIN" gateway run || true

echo "=========================================================="
echo "⚠️ Gateway stopped or waiting for WhatsApp pairing."
echo "👉 Run: docker exec -it chief-of-staff-agent /opt/hermes/.venv/bin/hermes whatsapp"
echo "=========================================================="
tail -f /dev/null
