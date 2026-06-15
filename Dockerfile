FROM nousresearch/hermes-agent:latest

# Set working directory inside the container
WORKDIR /opt/data

# Elevate privileges to install system packages
USER root

# Install system dependencies (cron, sqlite3, python3-pip)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    sqlite3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements for GCal, Todoist, and scraper plugins directly inside the virtualenv
RUN /opt/hermes/.venv/bin/python3 -m ensurepip --upgrade && \
    /opt/hermes/.venv/bin/python3 -m pip install --no-cache-dir \
    requests \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib
# Pre-install WhatsApp bridge dependencies to prevent 60-second npm timeout crashes on boot
RUN cd /opt/hermes/scripts/whatsapp-bridge && npm install

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
