import re

from discord import Intents
from discord.ext import commands
from db import SALES_CHANNELS, CLOCK_CHANNEL, TOKEN



intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message):
    channel_id = message.channel.id
    if message.author.bot:
        return

    if channel_id == CLOCK_CHANNEL:
        match = re.search(
            r"@(\w+).*?adding (\d+) hours, (\d+) minutes, (\d+) seconds",
            message.content
        )

        if match:
            nickname = match.group(1)
            hours = int(match.group(2))
            minutes = int(match.group(3))
            seconds = int(match.group(4))

            print(f"⏱️ {nickname} проработал {hours}ч {minutes}м {seconds}с")

    if channel_id in SALES_CHANNELS:
        match = re.findall(r'\d+', message.content.replace(' ', ''))
        price = int(match[0]) if match else None

        print(f"Продажа: {message.author} | {message.created_at} | {price}")

    await bot.process_commands(message)

bot.run(TOKEN)