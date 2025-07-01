import os
import discord
import logging

from collections import defaultdict
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import date, timedelta
from database import Database

load_dotenv()

TOKEN = os.getenv("LEADERBOARD_TOKEN")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

db = Database(
    minconn=1,
    maxconn=10,
    dbname=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT
)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

GROUPS = db.get_group_channels()
UPDATE_CHATS = db.get_update_channels()

LEADERBOARD_CHAT = int(os.getenv("LEADERBOARD_CHAT"))


@tasks.loop(minutes=2)  # или поменяй на days=7 после тестов
async def send_team_leaderboard():
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    start_date = last_monday
    end_date = last_sunday
    logger.info(f"Start of report: {start_date}; End of report: {end_date}.")

    leaderboard = []

    for group_id, channel_ids in GROUPS.items():
        group_total = 0
        for channel_id in channel_ids:
            sales = db.get_sales_by_channel_and_date(channel_id, start_date, end_date)
            if not sales or not sales['sales_by_user']:
                logger.error(f"Sales is empty for {group_id} group.")
                continue
            for _, amount in sales['sales_by_user']:
                group_total += amount

        leaderboard.append((group_id, group_total))

    leaderboard.sort(key=lambda x: x[1], reverse=True)

    msg = f"💸  **SALES LEADERBOARD OF THE WEEK:**\n"
    msg += f"**Week: {start_date.isocalendar()[1]}**\n\n"

    if leaderboard:
        best_team = leaderboard[0][0]
        msg += f"**BEST TEAM 🚀**\n"
        msg += f"**TA-{best_team}**\n\n"
        msg += "------------------------------------------\n\n"

        for group_id, total_sales in leaderboard:
            msg += f"**TEAM TA-{group_id}**\n"
            msg += f"**Total Sales: {total_sales} EUR**\n\n"
    else:
        logger.info(f"There's no sales data for {group_id} group.")
        msg += "No sales data found.\n"

    channel = bot.get_channel(LEADERBOARD_CHAT)
    if channel:
        logger.info(f"A message has been sent to the {group_id} group.")
        await channel.send(msg)
    else:
        logger.error(f"Channel ID {LEADERBOARD_CHAT} not found for {group_id} group.")

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}.")
    send_team_leaderboard.start()


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN is not set")
    bot.run(TOKEN)