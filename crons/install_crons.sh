#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
# install_crons.sh - Installs the cron jobs for the Personal Chief of Staff

CRON_DIR="$HOME/.hermes/crons"
TEMP_CRON=$(mktemp)

# Get current crontab, ignore error if it doesn't exist
crontab -l > "$TEMP_CRON" 2>/dev/null || true

# Check if we already installed our crons
if grep -q "hermes/crons" "$TEMP_CRON"; then
    echo "Crons already seem to be installed. Removing old entries..."
    sed -i '/hermes\/crons/d' "$TEMP_CRON"
fi

echo "Adding new cron entries..."

# Daily brief at 7:00 AM every weekday (Monday to Friday)
echo "0 7 * * 1-5 $CRON_DIR/daily_brief.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"

# Blog reminder at 9:00 AM on Monday and Friday
echo "0 9 * * 1,5 $CRON_DIR/blog_reminder.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"

# Blog follow-up at 4:00 PM on Monday and Friday
echo "0 16 * * 1,5 $CRON_DIR/blog_followup.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"

# LinkedIn engagement at 8:00 AM and 5:00 PM every weekday
echo "0 8 * * 1-5 $CRON_DIR/linkedin_engagement.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"
echo "0 17 * * 1-5 $CRON_DIR/linkedin_engagement.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"

# Weekly content batch at 6:00 PM on Sunday
echo "0 18 * * 0 $CRON_DIR/weekly_content_batch.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"

# Opportunity Aggregator at 12:00 PM every weekday (Monday to Friday)
echo "0 12 * * 1-5 $CRON_DIR/opportunity_aggregator.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"

# Weekly routine self-training analysis at 9:00 PM on Sunday
echo "0 21 * * 0 $CRON_DIR/weekly_routine_analysis.sh >> $HOME/.hermes/cron.log 2>&1" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo "Crontab installed successfully. List of active crons:"
crontab -l
