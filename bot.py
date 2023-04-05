# connections and local python files
import os
from dotenv import load_dotenv
import socket
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import bot_functions

# discord
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Converter, Context
from discord import Embed

# standard
import logging
import numpy as np
import pandas as pd
import pytz
from datetime import datetime, timedelta

# timing and scheduling
import aiocron
import asyncio
from asyncio import Lock

# check host
host_nm = socket.gethostname()
local_mode = True if host_nm == "MJT" else False

# create logger
formatter = logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(f"files/bot_{host_nm}.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# connection details
load_dotenv()
TOKEN = os.getenv('CROSSWORD_BOT')
my_intents = discord.Intents.all()
my_intents.message_content = True

# bot setup
bot = commands.Bot(command_prefix="/", intents=my_intents)

active_channel_names = ["crossword-corner", "game-scores", "bot-test"]

# set mySQL details
sql_pass = os.getenv("SQLPASS")
sql_user = os.getenv("SQLUSER")
sql_host = os.getenv("SQLHOST")
sql_port = os.getenv("SQLPORT")
database = os.getenv("SQLDATA")
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"

# helps lock tasks?
task_lock = Lock()

# accept multiple words in command arguments/parameters?
class BracketSeparatedWords(Converter):
    async def convert(self, ctx: Context, argument: str) -> list:
        # return argument.split("[")[1].split("]")[0].split()
        argument = argument.strip("[]")
        return argument.split()

# emoji map for confirming game scores
emoji_map = {
            'worldle': '🌎',
            '#Worldle': '🌎',
            'Factle.app': '📈',
            'Wordle': '📚',
            'boxofficega.me': '🎥'
        }

# connect
@bot.event
async def on_connect():
    logger.info(f"Bot has been reconnected to {socket.gethostname()}")

# disconnect
@bot.event
async def on_disconnect():
    logger.warning(f"Bot has been disconnected from {socket.gethostname()}")

# startup
@bot.event
async def on_ready():

    # get time
    now_txt = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # Initialize empty all_users dataframe
    all_users = pd.DataFrame(columns=["guild_id", "guild_nm", "member_id", "member_nm", "insert_ts"])

    # add all users to dataframe
    for guild in bot.guilds:
        logger.debug(f"Connected to {guild.name}")

        # get user list into csv
        members = guild.members
        member_data = []
        for member in members:
            guild_id = guild.id
            guild_nm = guild.name
            member_id = member.id
            member_nm = str(member)
            member_data.append([guild_id, guild_nm, member_id, member_nm, now_txt])
        guild_users = pd.DataFrame(member_data, columns=["guild_id", "guild_nm", "member_id", "member_nm", "insert_ts"])
        all_users = pd.concat([all_users, guild_users], ignore_index=True)

    # save users to database
    engine = create_engine(sql_addr)
    all_users.to_sql('user_history', con=engine, if_exists='append', index=False)

    # start timed tasks
    if not auto_post_the_mini.is_running():
        auto_post_the_mini.start()

    # confirm
    logger.debug(f"{bot.user.name} is ready!")

# read channel messages
@bot.event
async def on_message(message):
    
    # check channel
    if message.channel.name not in active_channel_names:
        return

    # ignore self
    if message.author == bot.user:
        return

    # get message detail
    msg_now = datetime.now(pytz.timezone('US/Eastern'))
    msg_time = msg_now.strftime("%Y-%m-%d %H:%M:%S")
    msg_text = str(message.content)
    user_id = message.author.name + "#" + message.author.discriminator #str(message.author.display_name)

    # check all potential score posts
    pref_list = ['#Worldle', 'Wordle', 'Factle.app', 'boxofficega.me', 'Atlantic', 'The Atlantic']
    for game_prefix in pref_list:
        if str.lower(msg_text).startswith(str.lower(game_prefix)):
            logger.debug(f"{user_id} posted a score for {game_prefix}")

            if game_prefix in ['Atlantic', 'The Atlantic', 'atlantic']:
                game_prefix = 'atlantic'

            # send to score scraper
            response = bot_functions.add_score(game_prefix, user_id, msg_text)

            # react with proper emoji
            emoji = '❌' if not response[0] else emoji_map.get(game_prefix.lower(), '✅')         
            await message.add_reaction(emoji)

    # run the message check
    await bot.process_commands(message)

# ****************************************************************************** #
# automatic posting
# ****************************************************************************** #

# post daily mini warning
async def post_warning():
    async with task_lock:
        await asyncio.sleep(5)

        # post warning in each active channel for each guild
        for guild in bot.guilds:
            logger.debug(f"Posting Mini Warning for {guild.name}")
            for channel in guild.channels:
                if channel.name in active_channel_names and isinstance(channel, discord.TextChannel):
                    await channel.send(f""" Mini expires soon (test) """)

# weekday warning
@aiocron.crontab('0 21 * * 1-5')
async def cron_warning_weekdays():
    await post_warning()

# weekend warning
@aiocron.crontab('0 17 * * 6,7')
async def cron_warning_weekends():
    await post_warning()

# post daily mini final
async def post_mini():
    async with task_lock:
        await asyncio.sleep(5)
        game_name = 'mini' # later we'll add other automatic posting

        # post warning in each guild
        for guild in bot.guilds:
            logger.debug(f"Posting Final {game_name.capitalize()} Leaderboard for {guild.name}")
            img = bot_functions.get_leaderboard(guild_nm=guild.name, game_name=game_name)
            for channel in guild.channels:
                if channel.name in active_channel_names and isinstance(channel, discord.TextChannel):
                    await channel.send(f""" Positng the final {game_name.capitalize()} Leaderboard now...""")
                    await asyncio.sleep(5)
                    await channel.send(file=discord.File(img))

# weekday final post
@aiocron.crontab('0 22 * * 1-5')
async def cron_recap_weekdays():
    await post_mini()

# weekend final post
@aiocron.crontab('0 18 * * 6,7')
async def cron_recap_weekends():
    await post_mini()

# ****************************************************************************** #
# end automatic posting
# ****************************************************************************** #

# every 5 minutes check for mini
@tasks.loop(minutes=5)
async def auto_fetch_the_mini():

    # run get_mini
    response = bot_functions.get_mini()

    # if no mini yet, don't do anything
    if not response[0]:
        pass

    logger.debug("Got mini.")

# command to get other leaderboards (only mini is working right now)
@bot.command(name='get', aliases=['mini', 'wordle', 'factle', 'worldle', 'atlantic', 'boxoffice'])
async def get(ctx, *, time_frame='daily'):
    
    # clarify request
    user_id = ctx.author.name
    guild_nm = ctx.guild.name
    time_frame = str.lower(time_frame)
    game_name = ctx.invoked_with

    # print
    logger.debug(f"{user_id} requested {time_frame} {game_name} leaderboard.")

    # only daily available right now
    if time_frame != 'daily':
        return await ctx.channel.send("Sorry, but only daily leaderboards are available right now.")

    # get the data
    try:
        img = bot_functions.get_leaderboard(guild_nm, game_name)
        await ctx.channel.send(file=discord.File(img))       
    except Exception as e:
        error_message = f"Error getting {game_name} leaderboard: {str(e)}"
        await ctx.channel.send(error_message)


# getting missed scores
@bot.command(name='rescan', description="Rescan the past X days of messages for missed scores")
async def rescan(ctx):
    user_id = ctx.author.name + "#" + ctx.author.discriminator
    days = 30
    print(f"User {user_id} requested rescan of {days} days")
    await process_missed_scores(ctx, days)


# actually getting them
async def process_missed_scores(ctx, days):
    today = datetime.utcnow()
    since = today - timedelta(days=days)
    
    # keep track
    missing_scores_added = 0
    
    # scan messages
    async for message in ctx.channel.history(before=today):  # after=since):
        
        # ignore bot messages
        if message.author == bot.user:
            continue
        
        # ignore other channels
        if message.channel.name not in active_channel_names:
            continue
        
        # get message text
        msg_text = str(message.content)
        user_id = message.author.name + "#" + message.author.discriminator
        msg_ts = message.created_at

        # Check to see if this is a game score and get the matching game prefix
        pref_list = ['#Worldle', 'Wordle', 'Factle.app', 'boxofficega.me', 'Atlantic', 'The Atlantic']
        game_prefix = next((p for p in pref_list if str.lower(msg_text).startswith(str.lower(p))), None)
        if game_prefix is None:
            continue
        
        print(f"Found game prefix: {game_prefix}")
        # see if it's already been added
        score_already_added = False
        for reaction in message.reactions:
            if reaction.me:
                score_already_added = True
                break
    
        if score_already_added:
            continue

        # else
        print(f"Found score not added from {user_id} on {message.channel.name}. Message sent at: {msg_ts}. Text is: {msg_text}")

        # add the score
        response = bot_functions.add_score(game_prefix, user_id, msg_text)
        missing_scores_added += 1

        # determine response emoji if response is not True
        emoji = '❌' if not response[0] else emoji_map.get(game_prefix.lower(), '✅')
        await message.add_reaction(emoji)

    await ctx.send(f"Rescanned messages from the last {days} days. Added {missing_scores_added} missing scores.")


# run bot
bot.run(TOKEN)
