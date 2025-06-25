import re

from discord import Intents
from discord.ext import commands
from database import Database

import os
from dotenv import load_dotenv

load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")
SALES_CHANNELS = [
    int(os.getenv("TEST_1")),
    int(os.getenv("TEST_2"))
]
CLOCK_CHANNEL = int(os.getenv("TEST_3"))


# SALES_CHANNELS = [
#     int(os.getenv("F2F_TA_09_JOWISSA")),
#     int(os.getenv("F2F_TA_09_RIAD")),
#     int(os.getenv("F2F_TA_09_GENNA")),
#     int(os.getenv("F2F_TA_09_GLYDEL")),
#     int(os.getenv("F2F_TA_010_GENNA")),
#     int(os.getenv("F2F_TA_010_PATRIC")),
#     int(os.getenv("F2F_TA_011_GENNA")),
#     int(os.getenv("F2F_TA_012_GLYDEL")),
#     int(os.getenv("F2F_TA_012_GENNA")),
#     int(os.getenv("F2F_TA_013_IVY"))
# ]

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

try:
    conn = db.get_connection()
    print("✅ Успешное подключение к базе данных")
    db.release_connection(conn)
except Exception as e:
    print(f"❌ Ошибка подключения к БД: {e}")


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
            username = match.group(1)
            hours = int(match.group(2))
            minutes = int(match.group(3))
            seconds = int(match.group(4))

            print(f"⏱️ {username} проработал {hours}ч {minutes}м {seconds}с")
            db.insert_clocked_time(
                username=username,
                hours=hours,
                minutes=minutes,
                seconds=seconds,
                channel_id=CLOCK_CHANNEL
            )

    if channel_id in SALES_CHANNELS:
        match = re.findall(r'\d+', message.content.replace(' ', ''))
        price = int(match[0]) if match else None

        if price:
            print(f"Продажа: {message.author} | {message.created_at} | {price}")
            db.insert_sale(
                username=str(message.author),
                channel_id=channel_id,
                price=price,
                timestamp=message.created_at
            )

    await bot.process_commands(message)

bot.run(TOKEN)