import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.monitoring.github_webhook import router as webhook_router
from app.monitoring.drips_poller import poll_drips
from app.notifiers.discord_bot import start_discord_bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(poll_drips())
    asyncio.create_task(start_discord_bot())
    yield

app = FastAPI(title="Wave-Watch Discovery Bot", lifespan=lifespan)
app.include_router(webhook_router)

@app.get("/health")
def health():
    return {"status": "ok"}
