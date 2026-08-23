FROM nousresearch/hermes-agent:latest

WORKDIR /opt/data

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    sqlite3 \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements for GCal, Todoist, Buffer, and Scrapers inside the virtualenv
RUN /opt/hermes/.venv/bin/python3 -m pip install --no-cache-dir \
    requests \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib \
    pyyaml

# Pre-install WhatsApp bridge dependencies to prevent startup timeouts
RUN if [ -d "/opt/hermes/scripts/whatsapp-bridge" ]; then cd /opt/hermes/scripts/whatsapp-bridge && npm install; fi

# Pre-stage Chief of Staff skills, plugins, and crons
COPY skills /opt/app/skills/
COPY plugins /opt/app/plugins/
COPY crons /opt/app/crons/
COPY setup.sh /opt/app/setup.sh
COPY entrypoint.sh /opt/app/entrypoint.sh

# Ensure all scripts are executable
RUN chmod +x /opt/app/crons/*.sh /opt/app/setup.sh /opt/app/entrypoint.sh

# Expose Hermes Dashboard Port
EXPOSE 8642

# Boot utilizing production entrypoint
ENTRYPOINT ["/opt/app/entrypoint.sh"]
