import telebot
from app.config import settings
from app.models import WaveIssue

_bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)

async def send_telegram_alert(issue: WaveIssue):
    text = (
        f"🚀 *New Wave Issue Found!*\n"
        f"*Project:* {issue.repo_name}\n"
        f"*Reward:* {issue.points} Points\n"
        f"[Claim & Fix]({issue.url})"
    )
    _bot.send_message(settings.TELEGRAM_CHAT_ID, text, parse_mode="Markdown")
