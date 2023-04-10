# connections and local python files
import os
import socket
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import bot_functions
from config import credentials, sql_addr

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
import asyncio
from asyncio import Lock

# environment variables
load_dotenv()
TOKEN = os.getenv('CROSSWORD_BOT')

# create logger
formatter = logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(f"files/bot_{socket.gethostname()}.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# discord connection details
my_intents = discord.Intents.all()
my_intents.message_content = True

# bot setup
bot = commands.Bot(command_prefix="/", intents=my_intents)
bot_channels = bot_functions.get_bot_channels()


# remove this!!!!
active_channel_names = ["crossword-corner", "game-scores", "bot-test"]



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

    # get latest user list
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
    engine = create_engine(sql_addr)
    all_users.to_sql('user_history', con=engine, if_exists='append', index=False)

    # Start timed tasks
    tasks_to_start = [auto_fetch, auto_warn, auto_post]
    for task in tasks_to_start:
        if not task.is_running():
            task.start()

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
# tasks
# ****************************************************************************** #

# every few minutes check for mini (set to 15 for now)
@tasks.loop(minutes=1)
async def auto_fetch():

    # get new mini and save to database
    bot_functions.get_mini()
    logger.debug("Got latest mini scores from NYT")

    # for each guild, see if the mini leader has changed since the last run
    for guild in bot.guilds:
        changed = bot_functions.mini_leader_changed(guild.id)

        # if changed, post new leaderboard to main games channel
        if changed:
            img = bot_functions.get_leaderboard(guild_id=str(guild.id), game_name='mini')
            main_channel = bot_channels.get(str(guild.id))

            # post to main channel
            if main_channel and main_channel['channel_id_int'] in [channel.id for channel in guild.channels]:
                send_channel = bot.get_channel(main_channel['channel_id_int'])
                
                # send message
                await send_channel.send("Someone else took the lead!")
                await send_channel.send(file=discord.File(img))

# post daily mini warning
async def post_warning():
    async with task_lock:
        await asyncio.sleep(5)

        # post warning in each active channel for each guild
        for guild in bot.guilds:
            logger.debug(f"Posting Mini Warning for {guild.name}")
            for channel in guild.channels:
                if channel.name in active_channel_names and isinstance(channel, discord.TextChannel):
                    await channel.send(f""" Mini expires in one hour! """)

# post daily mini final
async def post_mini():
    async with task_lock:
        await asyncio.sleep(5)

        # only one game
        game_name = 'mini'

        # post warning in each guild
        for guild in bot.guilds:
            logger.debug(f"Posting Final {game_name.capitalize()} Leaderboard for {guild.name}")
            img = bot_functions.get_leaderboard(guild_id=str(guild.id), game_name=game_name)
            for channel in guild.channels:
                if channel.name in active_channel_names and isinstance(channel, discord.TextChannel):
                    await channel.send(f"""Positng the final {game_name.capitalize()} Leaderboard now...""")
                    await asyncio.sleep(5)
                    await channel.send(file=discord.File(img))

# timer for warning
@tasks.loop(minutes=1)
async def auto_warn():
    now = datetime.now(pytz.timezone('US/Eastern'))
    cutoff_hour = 17 if now.weekday() in [5, 6] else 21
    if now.minute == 0 and now.hour == cutoff_hour:
        logger.debug("Time to warn!")
        await post_warning()

# timer for final post
@tasks.loop(minutes=1)
async def auto_post():
    now = datetime.now(pytz.timezone('US/Eastern'))
    post_hour = 18 if now.weekday() in [5, 6] else 22
    if now.minute == 0 and now.hour == post_hour:
        logger.debug("Time to post final!")
        await post_mini()

# ****************************************************************************** #
# end tasks
# ****************************************************************************** #

# command to get other leaderboards (only mini is working right now)
@bot.command(name='get', aliases=['mini', 'wordle', 'factle', 'worldle', 'atlantic', 'boxoffice'])
async def get(ctx, *, time_frame='daily'):
    
    # clarify request
    user_id = ctx.author.name
    guild_id = str(ctx.guild.id)
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
        img = bot_functions.get_leaderboard(guild_id, game_name)
        await ctx.channel.send(file=discord.File(img))       
    except Exception as e:
        error_message = f"Error getting {game_name} leaderboard: {str(e)}"
        await ctx.channel.send(error_message)


# getting missed scores
@bot.command(name='rescan', description="Rescan the past 30 days of messages for missed scores")
async def rescan(ctx):
    user_id = ctx.author.name + "#" + ctx.author.discriminator
    days = 30
    logger.debug(f"User {user_id} requested rescan in channel {ctx.channel.name}")
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
        
        # see if it's already been added
        score_already_added = False
        for reaction in message.reactions:
            if reaction.me:
                score_already_added = True
                break
    
        if score_already_added:
            continue

        # add the score
        response = bot_functions.add_score(game_prefix, user_id, msg_text)
        missing_scores_added += 1

        # determine response emoji if response is not True
        emoji = '❌' if not response[0] else emoji_map.get(game_prefix.lower(), '✅')
        await message.add_reaction(emoji)

    await ctx.send(f"Added {missing_scores_added} missing scores.")


# run bot
bot.run(TOKEN)
