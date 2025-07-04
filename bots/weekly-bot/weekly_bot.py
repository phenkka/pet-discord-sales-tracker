import os
import discord
import logging

from collections import defaultdict
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import date, timedelta
from database import Database

load_dotenv()

TOKEN = os.getenv("REPORT_TOKEN")
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
MANAGEMENT = int(os.getenv("MANAGEMENT"))
CLOCK = int(os.getenv("CLOCK_CHAT"))


@tasks.loop(minutes=10080)
async def send_weekly_report():
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    start_date = last_monday
    end_date = last_sunday
    logger.info(f"WEEKLY: Start of report: {start_date}; End of report: {end_date}.")

    for group_id, channel_ids in GROUPS.items():
        update_channel_id = UPDATE_CHATS.get(group_id)
        if not update_channel_id:
            logger.error(f"WEEKLY: No UPDATE_CHAT for group {group_id}.")
            continue

        msg = f"💸 **WEEKLY SALES LEADERBOARD (Group TA-0{group_id})**\n"
        msg += f"**Date: **{start_date.strftime('%d %b')} till {end_date.strftime('%d %b')}\n\n"

        all_sales = []
        for channel_id in channel_ids:
            sales = db.get_sales_by_channel_and_date(channel_id, start_date, end_date)
            if not sales or not sales['sales_by_user']:
                logger.error(f"WEEKLY: Sales is empty for {group_id} group, channel {channel_id}.")
                continue
            all_sales.extend(sales['sales_by_user'])

        if not all_sales:
            logger.info(f"WEEKLY: There's no sales data for {group_id} group.")
            msg += "No sales data found.\n"
        else:
            user_totals = defaultdict(int)
            for username, amount in all_sales:
                user_totals[username] += amount

            for channel_id in channel_ids:
                sales = db.get_sales_by_channel_and_date(channel_id, start_date, end_date)
                # top_sales_day = sales['top_sales_day'][0]
                # top_sales_amount = sales['top_sales_day'][1]

            sales_per_month = 0
            top_chatter = ["", 0]
            works = db.get_clocked_time_by_channel_and_date(CLOCK, start_date, end_date)
            for username, total_sales in sorted(user_totals.items(), key=lambda x: x[1], reverse=True):
                for worker in works:
                    if worker[0] != username:
                        logger.error(f"WEEKLY: The information is incorrect on the seller for {group_id} group.")
                        continue
                    hours = worker[1].total_seconds() / 3600
                    avg = total_sales / hours if hours else 0
                    sales_per_month += total_sales
                    if top_chatter[1] < total_sales:
                        top_chatter[0] = username
                        top_chatter[1] = total_sales

                    msg += f"**@{username}**\n"
                    msg += f"**Sales: **{total_sales} EUR.\n"
                    msg += f"**Worked hours: **{hours:.2f} hours.\n"
                    msg += f"**Average Earnings per hour: **{avg:.2f} EUR/hour.\n"
                    # msg += f"**Best performing day: **{top_sales_day}\n\n"

            msg += f"--------------------------------------------------------------\n\n"
            msg += f"🚀 **Top Performing Chatter: **{top_chatter[0]}.\n"
            msg += f"💸 **Total Team Sales: **{sales_per_month} EUR.\n\n"
            msg += f"--------------------------------------------------------------"

        channel = bot.get_channel(update_channel_id)
        if channel:
            logger.info(f"WEEKLY: A message has been sent to the {group_id} group.")
            await channel.send(msg)
        else:
            logger.error(f"WEEKLY: Channel ID {update_channel_id} not found for {group_id} group.")

        management_channel = bot.get_channel(MANAGEMENT)
        if management_channel:
            await management_channel.send(msg)
        else:
            logger.error("WEEKLY: MANAGEMENT channel not found.")


@tasks.loop(minutes=1440)
async def send_daily_report():
    today = date.today()
    yesterday = today - timedelta(days=1)

    start_date = yesterday
    end_date = yesterday
    logger.info(f"DAILY: Start of report: {start_date}; End of report: {end_date}.")

    for group_id, channel_ids in GROUPS.items():
        update_channel_id = UPDATE_CHATS.get(group_id)
        if not update_channel_id:
            logger.error(f"No UPDATE_CHAT for group {group_id}.")
            continue

        msg = f"💸 **DAILY SALES LEADERBOARD (Group TA-0{group_id})**\n"
        msg += f"**Date: **{start_date.strftime('%d %b %Y')}\n\n"

        all_sales = []
        for channel_id in channel_ids:
            sales = db.get_sales_by_channel_and_date(channel_id, start_date, end_date)
            if not sales or not sales['sales_by_user']:
                logger.error(f"DAILY: Sales is empty for {group_id} group, channel {channel_id}.")
                continue
            all_sales.extend(sales['sales_by_user'])

        if not all_sales:
            logger.info(f"DAILY: There's no sales data for {group_id} group.")
            msg += "No sales data found.\n"
        else:
            user_totals = defaultdict(int)
            logger.info(f"{all_sales}")
            for username, amount in all_sales:
                user_totals[username] += amount
            logger.info(f"{user_totals}")

            sales_per_day = 0
            top_chatter = ["", 0]
            works = db.get_clocked_time_by_channel_and_date(CLOCK, start_date, end_date)
            logger.info(f"{works}")
            for username, total_sales in sorted(user_totals.items(), key=lambda x: x[1], reverse=True):
                for worker in works:
                    if worker[0] != username:
                        logger.error(f"DAILY: The information is incorrect on the seller for {group_id} group.")
                        continue
                    hours = worker[1].total_seconds() / 3600
                    avg = total_sales / hours if hours else 0
                    sales_per_day += total_sales
                    if top_chatter[1] < total_sales:
                        top_chatter[0] = username
                        top_chatter[1] = total_sales
                    logger.info(f"{username}, {total_sales}, {hours:.2f}, {avg:.2f}")

                    msg += f"**@{username}**\n"
                    msg += f"**Sales: **{total_sales} EUR.\n"
                    msg += f"**Worked hours: **{hours:.2f} hours.\n"
                    msg += f"**Average Earnings per hour: **{avg:.2f} EUR/hour.\n\n"

            msg += f"--------------------------------------------------------------\n\n"
            msg += f"🚀 **Top Performing Chatter: **{top_chatter[0]}.\n"
            msg += f"💸 **Total Team Sales: **{sales_per_day} EUR.\n\n"
            msg += f"--------------------------------------------------------------"

        channel = bot.get_channel(update_channel_id)
        if channel:
            logger.info(f"DAILY: A message has been sent to the {group_id} group.")
            await channel.send(msg)
        else:
            logger.error(f"DAILY: Channel ID {update_channel_id} not found for {group_id} group.")

        management_channel = bot.get_channel(MANAGEMENT)
        if management_channel:
            await management_channel.send(msg)
        else:
            logger.error("WEEKLY: MANAGEMENT channel not found.")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}.")
    send_weekly_report.start()
    send_daily_report.start()


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN is not set")
    bot.run(TOKEN)