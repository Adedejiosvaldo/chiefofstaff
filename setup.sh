#!/bin/bash

# setup.sh - Installs Hermes Agent and sets up the Personal Chief of Staff configuration.

set -e

echo "Starting Personal Chief of Staff Setup..."

# 1. Install Hermes Agent
echo "Installing Hermes Agent..."
if ! command -v hermes &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
    echo "Hermes Agent installed successfully."
else
    echo "Hermes Agent is already installed."
fi

# 2. Setup Directory Structure
echo "Setting up ~/.hermes directories..."
HERMES_DIR="$HOME/.hermes"
mkdir -p "$HERMES_DIR/skills"
mkdir -p "$HERMES_DIR/plugins"
mkdir -p "$HERMES_DIR/crons"
mkdir -p "$HERMES_DIR/honcho"
mkdir -p "$HERMES_DIR/platforms/whatsapp/session"
chmod 700 "$HERMES_DIR"

# 3. Copy files to ~/.hermes
echo "Copying skills, plugins, and crons to ~/.hermes..."
cp -r skills/* "$HERMES_DIR/skills/" 2>/dev/null || true
cp -r plugins/* "$HERMES_DIR/plugins/" 2>/dev/null || true
cp -r crons/* "$HERMES_DIR/crons/" 2>/dev/null || true

# 4. Setup .env file
echo "Setting up configuration (.env)..."
if [ ! -f "$HERMES_DIR/.env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example "$HERMES_DIR/.env"
        echo "Created ~/.hermes/.env from .env.example. Please edit it to add your API keys."
    else
        echo "Warning: .env.example not found in the current directory."
    fi
else
    echo "~/.hermes/.env already exists."
fi

echo "=========================================================="
echo "Setup complete!"
echo "Next steps:"
echo "1. Edit ~/.hermes/.env and add your API keys (Anthropic, Groq, Buffer, etc)."
echo "2. Run 'hermes setup' to configure Claude API."
echo "3. Run 'hermes whatsapp' to scan the QR code and pair your device."
echo "4. Set up cron jobs using the scripts provided in ~/.hermes/crons/."
echo "=========================================================="
