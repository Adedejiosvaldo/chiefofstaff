# ⚡ Personal Chief of Staff (Executive AI PA)

A self-hosted, WhatsApp-native personal AI agent built on **Hermes Agent (Nous Research)** and powered by **DeepSeek-V3** and **Gemini 2.0 Flash**. Acts as your proactive Chief of Staff, aggressive accountability coach (Oya), and technical ghostwriter.

---

## 🌟 Core Features

- **📱 WhatsApp Native**: Operates entirely inside your WhatsApp chats with 1-touch actions (`1`, `2`, `ship`, `done`).
- **🌅 Executive Morning Briefs (7:00 AM)**: Pulls Google Calendar, Todoist, unpushed local commits + GitHub pushes ([Adedejiosvaldo](https://github.com/Adedejiosvaldo)), and pre-drafts a high-impact LinkedIn post in your authentic writing voice.
- **🎯 5:00 PM Accountability Coach**: Scans open tasks, audits tomorrow's calendar for open deep-work blocks, and nudges you to complete commitments.
- **🎮 Oya Gamification & Dynamic Trivia Engine**:
  - Streak tracking (🔥), Heart budget (💖 5/5), Streak Freezes (🧊), and XP level progression.
  - **Dynamic On-The-Fly Trivia Challenges**: Generates unpredictable, brutally hard staff/principal-level questions in real-time across AI Engineering, Linux Kernel/DevOps, and Distributed Systems with savage rating breakdowns.
- **🌐 DevOps & Relocation Opportunity Radar**: Scrapes international remote DevOps/SRE roles outside Africa (US, UK, EU) and tags matches with `✈️ [VISA / RELOCATION SPONSORSHIP]`.
- **✍️ Weekly Tech Digest**: Aggregates top LLM model releases, distributed systems papers, and cloud post-mortems on the weekend.
- **💰 Ultra-Low-Cost (<$1.00/Month)**: Uses DeepSeek-V3 for conversational intelligence and Gemini 2.0 Flash for background audits via OpenRouter.

---

## 🚀 Quick Deployment (Docker)

### 1. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and fill in your keys:
- `OPENROUTER_API_KEY`: Get from [openrouter.ai/keys](https://openrouter.ai/keys)
- `TODOIST_API_TOKEN`: Get from [Todoist Developer Integrations](https://todoist.com/app/settings/integrations/developer)
- `BUFFER_ACCESS_TOKEN`: For automatic LinkedIn scheduling
- `WHATSAPP_ALLOWED_USERS`: Your phone number with country code (e.g. `2348012345678`)

### 2. Start Container
```bash
docker compose up -d --build
```

### 3. Pair WhatsApp
Scan the QR code to connect your WhatsApp session:
```bash
docker exec -it chief-of-staff-agent /opt/hermes/.venv/bin/hermes whatsapp
```

---

## 💻 Local VM / Host Setup (Alternative)

If running without Docker:
```bash
./setup.sh
```
Follow the terminal prompts to configure keys, run `hermes whatsapp` to pair, and activate crons with `~/.hermes/crons/install_crons.sh`.

---

## 🧪 Automated Testing

Verify all 8 subsystems, database state, mock fallbacks, and plugin registrations:
```bash
python3 tests/test_all.py
```

---

## 📁 Architecture Overview

```text
chiefofstaff/
├── plugins/
│   ├── core/                    # Unified Core Integration Engine
│   │   ├── db.py                # Context-managed SQLite State & CRUD
│   │   ├── todoist.py           # Todoist REST API v2 Client
│   │   ├── calendar.py          # Google Calendar Client (Africa/Lagos)
│   │   ├── git_activity.py      # Universal Git Scanner & GitHub Events API
│   │   ├── opportunity.py       # DevOps & Relocation Opportunity Radar
│   │   ├── buffer.py            # Buffer LinkedIn Publishing Client
│   │   └── dynamic_trivia.py    # On-The-Fly Staff-Level Trivia Engine
│   ├── oya-gamification/        # Gamification & Streaks Toolset
│   ├── todoist/                 # Todoist Plugin
│   ├── google-calendar/         # Calendar Plugin
│   ├── git-activity/            # Git Activity Plugin
│   ├── opportunity-radar/       # Opportunity Radar Plugin
│   ├── buffer/                  # Buffer Plugin
│   └── notification-bridge/     # Outbound Cron Notification Toolset
├── crons/                       # Proactive Scheduled Routines
│   ├── daily_brief.py           # 7:00 AM Executive Briefing Generator
│   ├── nudge_coach.py           # 5:00 PM Accountability Nudge Generator
│   └── *.sh                     # System Cron Triggers
├── skills/                      # Agent Personas & Style Guides
│   ├── productivity/            # Life Organizer, Routine Analyzer, Tech Digest
│   └── writing/                 # Joseph Adewunmi Writer Voice & LinkedIn Ghostwriting
├── Dockerfile                   # Hardened Production Container
├── docker-compose.yml           # Multi-mount Deployment Compose
└── entrypoint.sh                # Container Bootstrapper & Cron Initializer
```
