import re
import logging

from discord import Intents
from discord.ext import commands
from database import Database

import os
from dotenv import load_dotenv

load_dotenv()


TOKEN = os.getenv("REPORT_TOKEN")
CLOCK_CHANNEL = int(os.getenv("CLOCK_CHAT"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CLOCK_CHANNEL = int(os.getenv("CLOCK_CHANNEL"))

POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")


intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

db = Database(
    minconn=1,
    maxconn=10,
    dbname=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT
)

SALES_CHANNELS = db.get_group_channels()

try:
    conn = db.get_connection()
    db.release_connection(conn)
except Exception as e:
    print(f"❌ Error: {e}")


@bot.event
async def on_message(message):
    channel_id = message.channel.id

    if channel_id == 1334830760674197524 and "clocked out" in message.content.lower():
        logger.info("📥 Обнаружено сообщение о завершении смены.")
        # Поиск ника (первое слово с @)
        mention_match = re.search(r'@(\w+)', message.content)
        if not mention_match:
            logger.warning(f"❌ Не удалось найти упоминание пользователя в сообщении: {message.content}")
            return

        username = mention_match.group(1)

        # Поиск времени (число + hour/minute/second)
        hours_match = re.search(r'(\d+)\s+hours?', message.content, re.IGNORECASE)
        minutes_match = re.search(r'(\d+)\s+minutes?', message.content, re.IGNORECASE)
        seconds_match = re.search(r'(\d+)\s+seconds?', message.content, re.IGNORECASE)

        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0
        seconds = int(seconds_match.group(1)) if seconds_match else 0

        logger.info(f"⏱️ {username} worked {hours}h {minutes}m {seconds}s")
        db.insert_clocked_time(
            username=username,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            channel_id=CLOCK_CHANNEL,
            timestamp=message.created_at
        )

    if channel_id in SALES_CHANNELS:
        match = re.findall(r'\d+', message.content.replace(' ', ''))
        price = int(match[0]) if match else None

        if price:
            logger.info(f"Sale: {message.author} | {message.created_at} | {price}")
            db.insert_sale(
                username=str(message.author.display_name),
                channel_id=channel_id,
                price=price,
                timestamp=message.created_at
            )

    await bot.process_commands(message)

bot.run(TOKEN)