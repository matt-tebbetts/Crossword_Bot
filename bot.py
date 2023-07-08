
# ****************************************************************************** #
# import packages
# ****************************************************************************** #

# connections and local python files
import os
import socket
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import bot_functions
from bot_camera import dataframe_to_image_dark_mode
from config import sql_addr

# discord
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Converter, Context
from discord import Embed
from discord import app_commands  # trying new method

# data processing
import logging
import numpy as np
import pandas as pd
import pytz
import json

# timing and scheduling
from datetime import date, datetime, timedelta
import asyncio

# ****************************************************************************** #
# set-up
# ****************************************************************************** #

# environment variables
load_dotenv()
TOKEN = os.getenv('CROSSWORD_BOT')

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(f"files/bot_{socket.gethostname()}.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(file_handler)

# discord connection details
my_intents = discord.Intents.all()
my_intents.message_content = True

# bot setup
bot = commands.Bot(command_prefix="/", intents=my_intents)
bot_channels = bot_functions.get_bot_channels()

# remove this!!!!
active_channel_names = ["crossword-corner", "game-scores", "bot-test"]

# accept multiple words in command arguments/parameters?
class BracketSeparatedWords(Converter):
    async def convert(self, ctx: Context, argument: str) -> list:
        # return argument.split("[")[1].split("]")[0].split()
        argument = argument.strip("[]")
        return argument.split()

# set game names and prefixes
game_prefixes = ['#Worldle', '#travle', '#travle_usa', '#travle_gbr',
                 'Wordle', 'Factle.app', 'boxofficega.me',
                 'Atlantic', 'Connections', '#Emovi',
                 'Daily Crosswordle']

# this helps prevent the bot from thinking that #travle is a prefix for #travle_usa
game_prefixes.sort(key=len, reverse=True)

game_prefix_dict = {
    'mini': 'Mini',
    'worldle': '#Worldle',
    'travle': '#travle',
    'travle_usa': '#travle_usa',
    'travle_gbr': '#travle_gbr',
    'factle': 'Factle.app',
    'boxoffice': 'boxofficega.me',
    'wordle': 'Wordle',
    'atlantic': 'Atlantic',
    'connections': 'Connections',
    'emovi': '#Emovi',
    'crosswordle': 'Daily Crosswordle'
}

# emoji map for confirming game scores
emoji_map = {
            '#worldle': '🌎',
            '#travle': '🌍',
            '#travle_usa': '🇺🇸',
            '#travle_gbr': '🇬🇧',
            'atlantic': '🌊',
            'factle.app': '📈',
            'wordle': '📚',
            'boxofficega.me': '🎥',
            '#emovi': '🎬',
            'connections': '🔢',
            'daily crosswordle': '🧩',
        }

# for calling the /get_leaderboard command (which has aliases)
list_of_game_names = list(game_prefix_dict.keys())
list_of_game_names.extend(['winners', 'my_scores'])

# ****************************************************************************** #
# connecting
# ****************************************************************************** #

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
            member_nm = str(member)[:-2] if str(member).endswith("#0") else str(member)
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

    msg_text = str(message.content)

    # check for game score
    for game_prefix in game_prefixes:

        # find prefix
        if str.lower(msg_text).startswith(str.lower(game_prefix)):

            # get message detail
            game_date = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")
            
            # get discord name
            author = message.author.name
            user_id = author[:-2] if author.endswith("#0") else author

            logger.debug(f"{user_id} posted a score for {game_prefix}")

            # send to score scraper
            response = bot_functions.add_score(game_prefix, game_date, user_id, msg_text)

            # react with proper emoji
            emoji = '❌' if not response[0] else emoji_map.get(game_prefix.lower(), '✅')         
            await message.add_reaction(emoji)
        
            # exit the loop since we found the prefix
            break

    # run the message check
    await bot.process_commands(message)

# ****************************************************************************** #
# tasks
# ****************************************************************************** #

# check nyt mini leaderboard every minute
@tasks.loop(minutes=1)
async def auto_fetch():

    # get new mini and save to database
    try:
        bot_functions.get_mini()
        logger.debug("Got latest mini scores from NYT")
    except Exception as e:
        logger.error(f"An error occurred while getting the latest mini scores: {e}")

    """ it's slow, that's why... keeps pinging the sql server
    ## disabled this part for now 6/25/2023 @ 9:30am -- enabled again 7/7/2023 @ 11:44am, not sure why it was disabled
    # for each guild, see if the mini leader has changed since the last run
    for guild in bot.guilds:
        try:
            changed = bot_functions.mini_leader_changed(guild.id)

            # if changed, post new leaderboard to games channel for that guild
            if changed:
                
                # get leaderboard image
                try:
                    img = bot_functions.get_leaderboard(guild_id=str(guild.id), game_name='mini')
                except Exception as e:
                    logger.error(f"An error occurred while getting the leaderboard image: {e}")
                    continue

                # get channel to post to
                main_channel_id = bot_functions.get_main_channel_for_guild(str(guild.id))
                send_channel = bot.get_channel(main_channel_id)

                # send message
                try:
                    await send_channel.send("Someone else took the lead!")
                    await send_channel.send(file=discord.File(img))
                except Exception as e:
                    logger.error(f"An error occurred while sending the message: {e}")

        except Exception as e:
            logger.error(f"An error occurred while checking if the mini leader has changed: {e}")
        """
    
# post daily mini warning
async def post_warning():
    async with asyncio.Lock():
        await asyncio.sleep(5)

        # post warning in each active channel for each guild
        for guild in bot.guilds:
            logger.debug(f"Posting Mini Warning for {guild.name}")
            for channel in guild.channels:
                if channel.name in active_channel_names and isinstance(channel, discord.TextChannel):
                    await channel.send(f""" Mini expires in one hour! """)

# post daily mini final
async def post_mini():
    async with asyncio.Lock():
        await asyncio.sleep(5)

        # only one game
        game_name = 'mini'

        # post warning in each guild
        for guild in bot.guilds:
            logger.debug(f"Posting Final {game_name.capitalize()} Leaderboard for {guild.name}")

            today = datetime.now(pytz.timezone('US/Eastern'))
            
            img = bot_functions.get_leaderboard(guild_id=str(guild.id), game_name=game_name, min_date=today, max_date=today)
            for channel in guild.channels:
                if channel.name in active_channel_names and isinstance(channel, discord.TextChannel):
                    await channel.send(f"""Posting the final {game_name.capitalize()} Leaderboard now...""")
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
# commands
# ****************************************************************************** #

# get leaderboards
@bot.command(name='get', aliases=list_of_game_names)
async def get(ctx, *, time_frame=None):
    
    # clarify request
    if ctx.author.discriminator == "0":
        user_nm = ctx.author.name
    else:
        user_nm = ctx.author.name + "#" + ctx.author.discriminator
    guild_id = str(ctx.guild.id)
    guild_nm = ctx.guild.name
    game_name = ctx.invoked_with
    
    # default time_frame to 'today' if not provided
    if time_frame is None:
        time_frame = 'today'
    time_frame = str.lower(time_frame)

    # print
    logger.debug(f"{guild_nm} user {user_nm} requested {game_name} leaderboard for {time_frame}.")

    # get the min_date and max_date based on the user's input
    date_range = bot_functions.get_date_range(time_frame)
    if date_range is None:
        return await ctx.channel.send("Invalid date range or format. Please try again with a valid date range or keyword (e.g., 'yesterday', 'last week', 'this month', etc.).")
    min_date, max_date = date_range

    # get the data
    try:
        
        # run new mini before pulling leaderboard
        if game_name == 'mini':
            mini_response = bot_functions.get_mini()
            logger.debug(f"Got latest mini scores from NYT")
        
        await asyncio.sleep(1) # wait a second before running query

        # pull leaderboard
        img = bot_functions.get_leaderboard(guild_id, game_name, min_date, max_date, user_nm)
        
        # send it
        await ctx.channel.send(file=discord.File(img))

    except Exception as e:
        error_message = f"Error getting {game_name} leaderboard: {str(e)}"
        await ctx.channel.send(error_message)

# request rescan
@bot.command(name='rescan')
async def rescan(ctx, game_to_rescan=None):
    today = datetime.now(pytz.timezone('US/Eastern'))
    since = today - timedelta(days=1)

    # if one game specified, create list with that game only
    if game_to_rescan is not None:
        if game_to_rescan in game_prefix_dict:
            game_prefixes_to_rescan = [game_prefix_dict[game_to_rescan]]
        else:
            await ctx.channel.send(f"The game {game_to_rescan} is not found.")
            return
    else:
        game_prefixes_to_rescan = game_prefixes

    # print since as a text with time
    since_text = since.strftime("%Y-%m-%d %H:%M:%S")
    await ctx.channel.send(f"Rescanning messages since {since_text}...")

    # start dataframe to keep track of re-added scores
    columns = ['Player', 'Game Date', 'Game Name', 'Scores Added']
    df = pd.DataFrame(columns=columns)

    # scan messages
    async for message in ctx.channel.history(before=today, after=since, oldest_first=False):
        msg_text = str(message.content)

        # check to see if it's a game score
        for game_prefix in game_prefixes_to_rescan:

            # if we find the prefix, add the score
            if str.lower(msg_text).startswith(str.lower(game_prefix)):

                # get message detail
                game_date = message.created_at.date()
                
                # get discord name
                author = message.author.name
                user_id = author[:-2] if author.endswith("#0") else author

                logger.debug(f"Found {user_id}'s {game_prefix} score from {game_date}")

                # send to score scraper
                response = bot_functions.add_score(game_prefix, game_date, user_id, msg_text)

                # react with proper emoji
                emoji = '❌' if not response[0] else emoji_map.get(game_prefix.lower(), '✅')         
                await message.add_reaction(emoji)
            
                # add to counter
                condition = (df['Player'] == user_id) & (df['Game Name'] == game_prefix) & (df['Game Date'] == game_date)

                if df[condition].any().any():
                    df.loc[condition, 'Scores Added'] += 1
                else:
                    # Add a new row to the DataFrame
                    new_row = pd.DataFrame({'Player': [user_id],
                                            'Game Date': [game_date],
                                            'Game Name': [game_prefix], 
                                            'Scores Added': [1]})
                    df = pd.concat([df, new_row], ignore_index=True)
                    
                # exit the loop since we found the prefix
                break

    # get image of dataframe from custom function
    img = dataframe_to_image_dark_mode(df, 
                                    img_filepath='files/images/rescan.png', 
                                    img_title=f"Rescan Summary",
                                    img_subtitle=f"Since {since.strftime('%Y-%m-%d')}")

    await ctx.channel.send(f"Rescan complete. Here are the results:", file=discord.File(img))

# run bot
bot.run(TOKEN)
