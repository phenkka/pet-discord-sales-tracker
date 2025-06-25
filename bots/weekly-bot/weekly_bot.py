import os
import discord

from collections import defaultdict
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import date, timedelta
from database import Database

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

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

GROUPS = defaultdict(list)
UPDATE_CHATS = {}

for key, value in os.environ.items():
    if key.startswith("GROUP_"):
        group_id = key.split("_")[1]
        GROUPS[group_id] = [int(x) for x in value.split(",")]
    elif key.startswith("UPDATE_CHAT_"):
        group_id = key.split("_")[2]
        UPDATE_CHATS[group_id] = int(value)

CLOCK = int(os.getenv("CLOCK_CHAT"))


@tasks.loop(minutes=2)
async def send_test_report():
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    start_date = last_monday
    end_date = last_sunday

    for group_id, channel_ids in GROUPS.items():
        update_channel_id = UPDATE_CHATS.get(group_id)
        if not update_channel_id:
            print(f"❌ No UPDATE_CHAT for group {group_id}")
            continue

        msg = f"💸 **WEEKLY SALES LEADERBOARD (Group {group_id})**\n"
        msg += f"**Date: **{start_date.strftime('%d %b')} till {end_date.strftime('%d %b')}\n\n"

        all_sales = []
        for channel_id in channel_ids:
            sales = db.get_sales_by_channel_and_date(channel_id, start_date, end_date)

            if not sales or not sales['sales_by_user']:
                continue
            all_sales.extend(sales['sales_by_user'])

        if not all_sales:
            msg += "No sales data found.\n"
        else:
            user_totals = defaultdict(int)
            for username, amount in all_sales:
                user_totals[username] += amount

            for channel_id in channel_ids:
                sales = db.get_sales_by_channel_and_date(channel_id, start_date, end_date)
                top_sales_day = sales['top_sales_day'][0]
                top_sales_amount = sales['top_sales_day'][1]

            works = db.get_clocked_time_by_channel_and_date(CLOCK, start_date, end_date)
            for username, total_sales in sorted(user_totals.items(), key=lambda x: x[1], reverse=True):
                for worker in works:
                    if worker[0] != username:
                        continue
                    hours = worker[1].total_seconds() / 3600
                    avg = total_sales / hours if hours else 0

                    msg += f"**@{username}**\n"
                    msg += f"**Sales: **{total_sales} EUR.\n"
                    msg += f"**Worked hours: **{hours:.2f} hours.\n"
                    msg += f"**Average Earnings per hour: **{avg:.2f} EUR/hour.\n"
                    msg += f"**Best performing day: **{top_sales_day}\n\n"

        channel = bot.get_channel(update_channel_id)
        if channel:
            await channel.send(msg)
        else:
            print(f"⚠️ Channel ID {update_channel_id} not found.")



@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    send_test_report.start()  # запускаем таймер


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN is not set")
    bot.run(TOKEN)
