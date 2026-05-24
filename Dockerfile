FROM nousresearch/hermes-agent:latest

# Set working directory inside the container
WORKDIR /opt/data

# Elevate privileges to install system packages
USER root

# Install system dependencies (cron, sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements for GCal, Todoist, and scraper plugins
RUN pip install --no-cache-dir \
    requests \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib

# Pre-stage our custom Chief of Staff skill, plugin, and cron configurations in a safe backup directory
COPY skills /opt/app/skills/
COPY plugins /opt/app/plugins/
COPY crons /opt/app/crons/
COPY setup.sh /opt/app/setup.sh
COPY entrypoint.sh /opt/app/entrypoint.sh

# Make sure all bash/shell scripts are fully executable
RUN chmod +x /opt/app/crons/*.sh /opt/app/setup.sh /opt/app/entrypoint.sh

# Expose the standard Hermes Dashboard Port
EXPOSE 8642

# Boot utilizing our custom production entrypoint
ENTRYPOINT ["/opt/app/entrypoint.sh"]
