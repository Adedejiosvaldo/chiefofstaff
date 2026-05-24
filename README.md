# Personal Chief of Staff Agent

A self-hosted, WhatsApp-native personal AI agent built on Hermes Agent (Nous Research) that acts as an aggressive accountability coach and Chief of Staff.

## Overview
This is not a passive assistant that waits for instructions. This agent takes charge of your routine:
- **Organizes Your Life**: Understands your schedule in-depth, suggests the best times to read based on your rhythm, and surfaces relevant materials.
- **Takes Charge**: It doesn't just ask "What do you want to do?". It presents you with what needs to be done today.
- **Accountability Coach**: It follows up on tasks. If you haven't written your Monday/Friday blog post, it will ask why and push you to block out time.
- **Proactive Drafting**: Pre-drafts LinkedIn posts based on your voice notes and interests, presenting them for a simple approval workflow (`ship`, `redo`, `kill`).

## Features
- **WhatsApp Native**: Operates entirely within WhatsApp.
- **LinkedIn Drafting & Queuing**: Drafts posts in your voice. Once you say `ship`, it automatically adds it to your Buffer queue.
- **Daily Briefs**: 7:00 AM weekday briefings with your schedule, top todos, and a pre-drafted post.
- **Blog Follow-ups**: Reminds you to write your blog on Monday and Friday, and follows up at 4:00 PM to ensure it's done.
- **Weekly Content Batch**: Drafts a batch of content every Sunday at 6:00 PM.

## Setup Instructions

1. **Clone this repository** (or copy its contents).
2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```
   This will install Hermes Agent, set up the `~/.hermes` directories, and copy over the custom skills, plugins, and cron scripts.
3. **Configure API Keys**:
   Edit the newly created `~/.hermes/.env` file and add your API keys (Anthropic, Groq, Buffer).
4. **Connect WhatsApp**:
   Run `hermes whatsapp` in your terminal and scan the QR code with your phone. Ensure `WHATSAPP_ALLOWED_USERS` in your `.env` is set to your number.
5. **Install Scheduled Tasks**:
   Run the cron installer to set up the automated routines:
   ```bash
   ~/.hermes/crons/install_crons.sh
   ```

## Workflow Example
- **7:00 AM**: Agent messages you on WhatsApp: "Here is your daily brief. You have 3 meetings today. I suggest moving the 2pm sync as your schedule is heavy. Here is a drafted LinkedIn post on OCR in Fintech. Reply `ship` to queue it."
- **You**: "ship"
- **Agent**: *Queues post via Buffer plugin*. "Done. Queued for 8am."
- **4:00 PM**: Agent messages: "Did you finish the blog post you were supposed to write today? If not, let's block 30 minutes right now."

## Components
- `skills/`: Custom instructions that dictate the agent's behavior (e.g., `life-organizer.md`, `linkedin-draft.md`).
- `plugins/`: Python scripts that extend the agent's capabilities (e.g., `buffer_plugin.py`).
- `crons/`: Bash scripts triggered by the system cron to initiate proactive conversations.

## Privacy & Security
All credentials, memory, and skills stay on your own infrastructure. No data is shared with external parties beyond the necessary API calls to LLMs and Buffer.
