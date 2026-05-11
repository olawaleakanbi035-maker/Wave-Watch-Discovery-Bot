# 🌊 Wave-Watch Discovery Bot

> Real-time alerts for new Drips Wave earning opportunities — delivered straight to your Discord and Telegram.

---

## 📖 Overview

Wave-Watch is a real-time notification engine built for developers who participate in [Drips Wave](https://www.drips.network/) programs. It continuously monitors the **Scoping phase** of all active Wave programs and instantly pings registered developers when new tasks matching their skills become available — so no high-point issue ever goes unnoticed.

### The Problem It Solves

Drips Wave programs release new issues in batches. Developers who check manually often miss high-value issues within the first few minutes — the window when claiming is most competitive. Wave-Watch eliminates that lag by pushing alerts the moment a new `Wave`-labelled issue is opened on GitHub or detected via the Drips API.

### Who It's For

- Freelance developers actively earning through Drips Wave
- Teams managing multiple Wave program contributions
- Anyone who wants to automate their opportunity pipeline

---

## ✨ Features

- **GitHub Webhook Integration** — Listens for `issues.opened` and `issues.labeled` events. Filters by `Wave` label and extracts point value from `Points-<N>` labels.
- **Drips API Polling** — Independently polls the Drips scoping endpoint on a configurable interval as a fallback and cross-check.
- **Discord Alerts** — Rich embedded messages with project name, reward points, and a direct claim link.
- **Telegram Alerts** — Markdown-formatted messages sent to a configured chat or group.
- **Deduplication** — In-memory seen-set prevents duplicate notifications for the same issue URL.
- **HMAC Signature Verification** — All incoming GitHub webhook payloads are verified using `X-Hub-Signature-256`.
- **Health Endpoint** — `GET /health` for uptime monitoring and load balancer checks.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                          │
│                                                             │
│   POST /webhook/github          GET /health                 │
│         │                                                   │
│         ▼                                                   │
│   HMAC Verification                                         │
│         │                                                   │
│         ▼                                                   │
│   Parse Wave Labels  ◄──── Drips API Poller (async loop)   │
│         │                          │                        │
│         └──────────┬───────────────┘                        │
│                    ▼                                        │
│             WaveIssue Model                                 │
│                    │                                        │
│         ┌──────────┴──────────┐                             │
│         ▼                     ▼                             │
│   Discord Notifier      Telegram Notifier                   │
│   (discord.py embed)    (pyTelegramBotAPI)                  │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
Wave-Watch Discovery Bot/
├── .env.example                 # Environment variable template
├── .gitignore
├── README.md
├── requirements.txt
└── app/
    ├── main.py                  # FastAPI entrypoint + lifespan tasks
    ├── config.py                # Pydantic settings loaded from .env
    ├── models.py                # WaveIssue Pydantic model
    ├── monitoring/
    │   ├── __init__.py
    │   ├── github_webhook.py    # POST /webhook/github (HMAC-verified)
    │   └── drips_poller.py      # Async polling loop against Drips API
    └── notifiers/
        ├── __init__.py
        ├── discord_bot.py       # discord.py rich embed alerts
        └── telegram_bot.py      # pyTelegramBotAPI Markdown alerts
```

---

## ⚙️ How It Works

### 1. GitHub Webhook Flow

When a new issue is opened or labelled in a monitored repo:

1. GitHub sends a `POST` to `/webhook/github`
2. The handler verifies the `X-Hub-Signature-256` HMAC signature
3. It checks for the `Wave` label — ignores anything without it
4. It extracts the point value from a `Points-<N>` label (e.g. `Points-500`)
5. A `WaveIssue` object is constructed and dispatched to both notifiers as background tasks

### 2. Drips Poller Flow

Running concurrently as an async background task:

1. Every `POLL_INTERVAL_SECONDS` (default: 60s), it hits the Drips scoping endpoint
2. Each returned issue is checked against an in-memory deduplication set
3. New issues are dispatched to Discord and Telegram

---

## 💻 Code Snippets

### WaveIssue Model (`app/models.py`)

```python
from pydantic import BaseModel

class WaveIssue(BaseModel):
    repo_name: str
    title: str
    points: int
    url: str
    skills: list[str] = []
```

### GitHub Webhook Handler (`app/monitoring/github_webhook.py`)

```python
@router.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    _verify_signature(body, request.headers.get("X-Hub-Signature-256", ""))

    payload = await request.json()
    labels = [l["name"] for l in payload["issue"].get("labels", [])]

    if "Wave" not in labels:
        return {"status": "not a wave issue"}

    points = next(
        (int(l.split("-")[1]) for l in labels if l.startswith("Points-")), 0
    )
    wave_issue = WaveIssue(
        repo_name=payload["repository"]["full_name"],
        title=payload["issue"]["title"],
        points=points,
        url=payload["issue"]["html_url"],
        skills=labels,
    )
    background_tasks.add_task(send_discord_alert, wave_issue)
    background_tasks.add_task(send_telegram_alert, wave_issue)
    return {"status": "notified"}
```

### Discord Alert (`app/notifiers/discord_bot.py`)

```python
async def send_discord_alert(issue: WaveIssue):
    await _client.wait_until_ready()
    channel = _client.get_channel(settings.DISCORD_CHANNEL_ID)
    embed = discord.Embed(title="🚀 New Wave Issue Found!", color=0x00FF00)
    embed.add_field(name="Project", value=issue.repo_name, inline=True)
    embed.add_field(name="Reward",  value=f"{issue.points} Points", inline=True)
    embed.add_field(name="Action",  value=f"[Claim & Fix]({issue.url})")
    await channel.send(embed=embed)
```

### Telegram Alert (`app/notifiers/telegram_bot.py`)

```python
async def send_telegram_alert(issue: WaveIssue):
    text = (
        f"🚀 *New Wave Issue Found!*\n"
        f"*Project:* {issue.repo_name}\n"
        f"*Reward:* {issue.points} Points\n"
        f"[Claim & Fix]({issue.url})"
    )
    _bot.send_message(settings.TELEGRAM_CHAT_ID, text, parse_mode="Markdown")
```

### Drips Poller (`app/monitoring/drips_poller.py`)

```python
_seen: set[str] = set()

async def poll_drips():
    while True:
        try:
            issues = await _fetch_scoping_issues()
            for issue in issues:
                if issue.url not in _seen:
                    _seen.add(issue.url)
                    await send_discord_alert(issue)
                    await send_telegram_alert(issue)
        except Exception as e:
            print(f"[Drips poller] error: {e}")
        await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)
```

---

## 🚀 Setup & Running

### Prerequisites

- Python 3.11+
- A Discord bot token with `Send Messages` + `Embed Links` permissions
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A GitHub repo with webhook access

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-org/wave-watch.git
cd wave-watch

# 2. Copy and fill in environment variables
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload
```

### Environment Variables (`.env`)

| Variable                  | Description                                      |
|---------------------------|--------------------------------------------------|
| `GITHUB_WEBHOOK_SECRET`   | Secret token set in your GitHub webhook settings |
| `DRIPS_API_URL`           | Base URL for the Drips API                       |
| `POLL_INTERVAL_SECONDS`   | How often to poll Drips (default: `60`)          |
| `DISCORD_BOT_TOKEN`       | Your Discord bot token                           |
| `DISCORD_CHANNEL_ID`      | Channel ID to post alerts in                     |
| `TELEGRAM_BOT_TOKEN`      | Your Telegram bot token                          |
| `TELEGRAM_CHAT_ID`        | Chat or group ID to send alerts to               |

---

## 🔗 GitHub Webhook Configuration

1. Go to your GitHub repo → **Settings → Webhooks → Add webhook**
2. Set **Payload URL** to `https://your-domain.com/webhook/github`
3. Set **Content type** to `application/json`
4. Set **Secret** to the same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. Select **Individual events** → check **Issues**
6. Save

Wave-Watch will now receive a ping every time an issue is opened or labelled. Only issues carrying both the `Wave` label and a `Points-<N>` label will trigger a notification.

---

## 🛡️ Security

- All webhook payloads are verified with HMAC-SHA256 before processing. Requests with missing or invalid signatures return `401 Unauthorized`.
- Secrets are loaded exclusively from environment variables — never hardcoded.
- The `.env` file is gitignored by default.

---

## 📦 Dependencies

| Package              | Purpose                        |
|----------------------|--------------------------------|
| `fastapi`            | Web framework / webhook server |
| `uvicorn`            | ASGI server                    |
| `pydantic-settings`  | Typed env config               |
| `httpx`              | Async HTTP client for polling  |
| `discord.py`         | Discord bot + embed alerts     |
| `pyTelegramBotAPI`   | Telegram bot alerts            |

---

## 📄 License

MIT
