import os
import discord

from collections import defaultdict
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import date, timedelta
from database import Database

load_dotenv()

TOKEN = os.getenv("BONUS_BOT_TOKEN")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

BONUS_CHANNEL = int(os.getenv("BONUS_CHANNEL", 0))

BONUS_THRESHOLDS = [
    (295, 5),
    (472, 10),
    (590, 15),
    (885, 20),
    (1180, 50),
    (1475, 55),
    (1770, 60),
    (2065, 80),
    (2360, 90),
    (2950, 100),
]

def get_bonus_for_revenue(revenue):
    bonus = 0
    for threshold, amount in BONUS_THRESHOLDS:
        if revenue >= threshold:
            bonus = amount
        else:
            break
    return bonus

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


@tasks.loop(minutes=5)
async def check_and_notify_bonuses():
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    this_sunday = this_monday + timedelta(days=6)

    start_date = this_monday
    end_date = this_sunday

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

    for user in users:
        accounts = []

        all_accounts_reached = True
        min_revenue = float('inf')

        for account in accounts:
            revenue = db.get_sales_by_user_and_date(account, start_date, end_date)
            if revenue < BONUS_THRESHOLDS[0][0]:
                all_accounts_reached = False
                break
            min_revenue = min(min_revenue, revenue)

        if all_accounts_reached:
            bonus = get_bonus_for_revenue(min_revenue)
            channel = bot.get_channel(BONUS_CHANNEL)
            if channel:
                await channel.send(
                    f"🎉 **{user}** unlocked a bonus: **${bonus} per account**! 🤑\n"
                    f"Gross revenue on all accounts (this week): **${min_revenue}**"
                )
            else:
                print(f"Channel ID {BONUS_CHANNEL} not found.")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_and_notify_bonuses.start()

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("BONUS_BOT_TOKEN is not set")
    bot.run(TOKEN)