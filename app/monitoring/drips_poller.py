import asyncio
import httpx
from app.config import settings
from app.models import WaveIssue
from app.notifiers.discord_bot import send_discord_alert
from app.notifiers.telegram_bot import send_telegram_alert

_seen: set[str] = set()

async def _fetch_scoping_issues() -> list[WaveIssue]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.DRIPS_API_URL}/waves/scoping")
        resp.raise_for_status()
        return [WaveIssue(**item) for item in resp.json()]

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
