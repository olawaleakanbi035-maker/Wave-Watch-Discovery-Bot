import discord
from app.config import settings
from app.models import WaveIssue

_client = discord.Client(intents=discord.Intents.default())

async def send_discord_alert(issue: WaveIssue):
    await _client.wait_until_ready()
    channel = _client.get_channel(settings.DISCORD_CHANNEL_ID)
    if not channel:
        return
    embed = discord.Embed(title="🚀 New Wave Issue Found!", color=0x00FF00)
    embed.add_field(name="Project", value=issue.repo_name, inline=True)
    embed.add_field(name="Reward", value=f"{issue.points} Points", inline=True)
    embed.add_field(name="Action", value=f"[Claim & Fix]({issue.url})")
    await channel.send(embed=embed)

async def start_discord_bot():
    await _client.start(settings.DISCORD_BOT_TOKEN)
