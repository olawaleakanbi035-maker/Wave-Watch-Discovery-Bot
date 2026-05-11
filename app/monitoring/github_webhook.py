import hashlib, hmac
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.config import settings
from app.models import WaveIssue
from app.notifiers.discord_bot import send_discord_alert
from app.notifiers.telegram_bot import send_telegram_alert

router = APIRouter()

def _verify_signature(body: bytes, sig_header: str):
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig_header or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")

@router.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    _verify_signature(body, request.headers.get("X-Hub-Signature-256", ""))

    payload = await request.json()
    action = payload.get("action")
    issue = payload.get("issue", {})

    if action not in ("opened", "labeled"):
        return {"status": "ignored"}

    labels = [l["name"] for l in issue.get("labels", [])]
    if "Wave" not in labels:
        return {"status": "not a wave issue"}

    points = next(
        (int(l.split("-")[1]) for l in labels if l.startswith("Points-")), 0
    )
    wave_issue = WaveIssue(
        repo_name=payload["repository"]["full_name"],
        title=issue["title"],
        points=points,
        url=issue["html_url"],
        skills=labels,
    )
    background_tasks.add_task(send_discord_alert, wave_issue)
    background_tasks.add_task(send_telegram_alert, wave_issue)
    return {"status": "notified"}
