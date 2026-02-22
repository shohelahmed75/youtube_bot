# 🤖 Stryker Bot — YouTube Live Stream Moderator

**Stryker Bot** is a Python-powered YouTube live stream moderator bot. It monitors your live chat in real-time and automates common tasks so you can focus on your content.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Auto-Detect Stream** | Automatically finds your active live broadcast — no manual VIDEO_ID needed |
| **Welcome Messages** | Greets first-time chatters with a customizable message |
| **Persistent Welcomes** | Remembers who's been welcomed across bot restarts |
| **Slash Commands** | Responds to `/discord`, `/specs`, `/socials` with predefined replies |
| **Command Aliases** | Each command supports multiple aliases (e.g., `/dc` → `/discord`) |
| **Command Cooldowns** | Prevents spam — configurable cooldown per command |
| **Poll Creation** | Creates native YouTube polls from chat (owner/mod only) |
| **Hot Reload** | Type `/reload` in chat to refresh commands without restarting |
| **Colored Logging** | Color-coded console output + persistent file logs |

---

## 📋 Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Google Cloud Project** with the **YouTube Data API v3** enabled
- **OAuth 2.0 Client ID** (Desktop application type)

---

## 🚀 Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/yt-bot.git
cd yt-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Enable YouTube Data API v3

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**
4. Search for **YouTube Data API v3** and click **Enable**

### 4. Create OAuth 2.0 Credentials

1. In Google Cloud Console, go to **APIs & Services → Credentials**
2. Click **+ CREATE CREDENTIALS → OAuth client ID**
3. If prompted, configure the **OAuth consent screen** first:
   - User type: **External**
   - Fill in the app name, support email, and developer email
   - Add scope: `https://www.googleapis.com/auth/youtube`
   - Add your Google account as a **test user**
4. Back in Credentials, select **Desktop app** as the application type
5. Click **Create** and **Download JSON**
6. Rename the downloaded file to `client_secret.json` and place it in the project root

### 5. Configure Environment Variables

Copy the example below into your `.env` file and fill in your values:

```env
# YouTube Data API v3
API_KEY=your-api-key-here

# OAuth 2.0
CLIENT_SECRET_FILE=client_secret.json

# Bot Settings
VIDEO_ID=                  # Leave empty to auto-detect your active stream!
BOT_PREFIX=/               # Command prefix (default: /)
WELCOME_MESSAGE=Welcome to the stream, {username}! 🎉
POLL_DURATION=5

# Spam Protection
COOLDOWN_SECONDS=5         # Seconds between repeated command replies

# Data Storage
DATA_DIR=data              # Directory for persistent data (welcomed users, logs)
```

### 6. Run the Bot

```bash
python run.py
```

Or use the module syntax:

```bash
python -m stryker
```

**CLI flags:**

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Enable debug-level logging |
| `--video VIDEO_ID` | Override the video ID from .env |

---

## ⚙️ Adding Custom Commands

Edit `commands.json` to add, modify, or remove commands:

```json
[
  {
    "action": "/discord",
    "aliases": ["/dc"],
    "reply": "Join our Discord: https://discord.gg/your-link"
  },
  {
    "action": "/specs",
    "aliases": ["/pc", "/setup"],
    "reply": "CPU: Ryzen 7 5800X | GPU: RTX 3070 | RAM: 32GB DDR4"
  }
]
```

**Hot reload:** Type `/reload` in chat (as stream owner) to reload commands live.

---

## 📊 Creating Polls

Stream owners and moderators can create polls:

```
/poll "What game should I play next?" "Minecraft" "Fortnite" "Valorant"
```

- 2–4 options (YouTube API limit)
- Each option must be wrapped in quotes

---

## 🗂️ Project Structure

```
YT BOT/
├── .env                          # Environment variables
├── .gitignore
├── requirements.txt
├── client_secret.json            # OAuth 2.0 credentials (you provide)
├── commands.json                 # Slash command definitions
├── run.py                        # Entry point
├── README.md
├── data/                         # Auto-created persistent storage
│   ├── welcomed_*.json           # Welcomed viewer IDs per stream
│   └── bot.log                   # Persistent log file
└── stryker/                      # Main package
    ├── __init__.py               # CLI and main()
    ├── __main__.py               # python -m stryker support
    ├── bot.py                    # Core bot loop
    ├── core/
    │   ├── auth.py               # OAuth 2.0 authentication
    │   ├── chat.py               # YouTube chat read/write + auto-detect
    │   └── config.py             # Settings loader
    ├── features/
    │   ├── commands.py           # Command router + cooldowns
    │   ├── welcome.py            # Persistent welcome tracker
    │   └── polls.py              # Poll creation
    └── utils/
        ├── logger.py             # Colored logging
        └── storage.py            # JSON persistence
```

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| **`HttpError 403: quota exceeded`** | Daily API limit hit. Wait 24 hours or request increase. |
| **`No active live broadcast found`** | Make sure you're live, or set `VIDEO_ID` in `.env`. |
| **Bot re-welcomes everyone** | Check `data/` folder — welcomed data should persist. |
| **Commands not responding** | Check cooldown (5s default), or type `/reload`. |
| **`ModuleNotFoundError`** | Run `pip install -r requirements.txt`. |

---

## 📜 License

This project is for personal/educational use. Please respect YouTube's [Terms of Service](https://www.youtube.com/t/terms) and [API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service).
# youtube_bot
