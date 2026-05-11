from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # GitHub
    GITHUB_WEBHOOK_SECRET: str

    # Drips
    DRIPS_API_URL: str = "https://api.drips.network"
    POLL_INTERVAL_SECONDS: int = 60

    # Discord
    DISCORD_BOT_TOKEN: str
    DISCORD_CHANNEL_ID: int

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str

    class Config:
        env_file = ".env"

settings = Settings()
