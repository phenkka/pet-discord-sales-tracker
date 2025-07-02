import os
import discord
import logging

from collections import defaultdict
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import date, timedelta
from database import Database

load_dotenv()

TOKEN = os.getenv("BONUS_TOKEN")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

BONUS_THRESHOLDS = []

def load_bonus_thresholds():
    global BONUS_THRESHOLDS
    BONUS_THRESHOLDS = db.get_bonus_thresholds() or []

# Загружаем пороги при старте
load_bonus_thresholds()

def get_bonus_for_revenue(revenue):
    bonus = 0
    for threshold, amount in BONUS_THRESHOLDS:
        if revenue >= threshold:
            bonus = amount
        else:
            break
    return bonus

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


@tasks.loop(minutes=5)
async def check_and_notify_bonuses():
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    start_date = last_monday
    end_date = last_sunday

    for group_id, channel_ids in GROUPS.items():
        update_channel_id = UPDATE_CHATS.get(group_id)
        if not update_channel_id:
            logger.warning(f"No UPDATE_CHAT for group {group_id}")
            continue

        msg = f"💸 **WEEKLY SALES LEADERBOARD (Group {group_id})**\n"
        msg += f"**Date: **{start_date.strftime('%d %b')} till {end_date.strftime('%d %b')}\n\n"

        # Current week
        weekly_sales = db.get_weekly_sales_by_channels_for_period(channel_ids, start_date, end_date)
        # Previous week
        prev_weekly_sales = db.get_weekly_sales_by_channels_for_period(channel_ids, start_date, end_date)
        prev_bonuses = {username: get_bonus_for_revenue(total_sales) for username, total_sales in (prev_weekly_sales or [])}

        if not weekly_sales:
            msg += "No sales for this week."
        else:
            msg += "**User | Total Sales | Bonus**\n"
            msg += ":---|:---:|:---:\n"
            for username, total_sales in weekly_sales:
                bonus = get_bonus_for_revenue(total_sales)
                msg += f"{username} | {total_sales} | {bonus}\n"
                prev_bonus = prev_bonuses.get(username, 0)
                if bonus > prev_bonus and bonus > 0:
                    # Congratulation for new bonus
                    congrats_msg = (
                        f"BONUS UNLOCKED!  💸 🔓\n\n"
                        f"Congratulations @{username}! You unlocked a new bonus! 🚀\n\n"
                        f"Bonus Reached:\nAmount: {bonus}"
                    )
                    channel = bot.get_channel(int(update_channel_id))
                    if channel and isinstance(channel, discord.TextChannel):
                        await channel.send(congrats_msg)
                        logger.info(f"Sent bonus unlocked message for {username} (bonus: {bonus}) to update chat {update_channel_id} (group {group_id})")
                    else:
                        logger.error(f"Text channel {update_channel_id} not found for group {group_id} (bonus unlocked message)")

        # Send weekly leaderboard
        channel = bot.get_channel(int(update_channel_id))
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(msg)
            logger.info(f"Sent weekly leaderboard to update chat {update_channel_id} (group {group_id})")
        else:
            logger.error(f"Text channel {update_channel_id} not found for group {group_id} (leaderboard)")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    load_bonus_thresholds()  # обновляем пороги при запуске
    check_and_notify_bonuses.start()

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("BONUS_BOT_TOKEN is not set")
    bot.run(TOKEN)