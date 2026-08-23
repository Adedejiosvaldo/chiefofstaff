#!/bin/bash
# setup.sh - Sets up the Personal Chief of Staff on the local host or VM.

set -e

echo "Starting Personal Chief of Staff Setup..."

# 1. Install Hermes Agent if needed
echo "Checking Hermes Agent installation..."
if ! command -v hermes &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
    echo "Hermes Agent installed successfully."
else
    echo "Hermes Agent is already installed."
fi

# 1b. Install Python Dependencies
echo "Installing custom plugin dependencies..."
pip3 install -q requests google-api-python-client google-auth-httplib2 google-auth-oauthlib

# 2. Setup Directory Structure
echo "Setting up ~/.hermes directories..."
HERMES_DIR="$HOME/.hermes"
mkdir -p "$HERMES_DIR/skills"
mkdir -p "$HERMES_DIR/plugins/core"
mkdir -p "$HERMES_DIR/crons"
mkdir -p "$HERMES_DIR/platforms/whatsapp/session"
chmod 700 "$HERMES_DIR"

# 3. Copy files to ~/.hermes
echo "Copying skills, plugins, and crons to ~/.hermes..."
cp -r skills/* "$HERMES_DIR/skills/" 2>/dev/null || true
cp -r plugins/* "$HERMES_DIR/plugins/" 2>/dev/null || true
cp -r crons/* "$HERMES_DIR/crons/" 2>/dev/null || true
if [ -f "data/SOUL.md" ]; then cp data/SOUL.md "$HERMES_DIR/SOUL.md"; fi

# 4. Setup .env file
echo "Setting up configuration (.env)..."
if [ ! -f "$HERMES_DIR/.env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example "$HERMES_DIR/.env"
        echo "Created ~/.hermes/.env from .env.example. Please edit it to add your API keys."
    fi
else
    echo "~/.hermes/.env already exists."
fi

echo "=========================================================="
echo "Setup complete!"
echo "Next steps:"
echo "1. Edit ~/.hermes/.env and add your OPENROUTER_API_KEY (or DEEPSEEK_API_KEY)."
echo "2. Run 'hermes whatsapp' to scan the QR code and pair your device."
echo "3. Run '~/.hermes/crons/install_crons.sh' to activate proactive scheduled routines."
echo "=========================================================="
