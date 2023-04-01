# main functions and connecting
import os
from dotenv import load_dotenv
import socket
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Converter, Context
from discord import Embed
import numpy as np
import asyncio
import random
import pandas as pd
import pytz
from datetime import datetime, timedelta
import inspect
import bot_functions
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# set global variables
host_nm = socket.gethostname()
local_mode = True if host_nm == "MJT" else False

# Create a formatter that includes a timestamp
formatter = logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler
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

# set mySQL details
sql_pass = os.getenv("SQLPASS")
sql_user = os.getenv("SQLUSER")
sql_host = os.getenv("SQLHOST")
sql_port = os.getenv("SQLPORT")
database = os.getenv("SQLDATA")
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"

# guilds and channel_ids
nerd_city = 672233217985871908
crossword_corner = 806881904073900042
bot_test = 813831098312294490
tebbetts_server = 349702892631883778
game_scores = 1058057309068197989

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
    auto_post_the_mini.start()

    # confirm
    logger.debug(f"{bot.user.name} is ready!")


# read channel messages
@bot.event
async def on_message(message):
    
    # check channel
    if message.channel.name not in ["crossword", "crossword-corner", "bot_tester", "bot-test", "game-scores"]:
        return

    # ignore self
    if message.author == bot.user:
        return

    # get message detail
    msg_now = datetime.now(pytz.timezone('US/Eastern'))
    msg_time = msg_now.strftime("%Y-%m-%d %H:%M:%S")
    msg_text = str(message.content)
    user_id = message.author.name + "#" + message.author.discriminator #str(message.author.display_name)

    old_msg = None
    # if they wrote "!add" then replace msg_text with the original message
    if msg_text == "!add":
        if message.reference.resolved:
            old_msg = await message.channel.fetch_message(message.reference.message_id)
            msg_text = str(old_msg.content)
            user_id = str(old_msg.author.name + "#" + old_msg.author.discriminator)

    # check all potential score posts
    pref_list = ['#Worldle', 'Wordle', 'Factle.app', 'boxofficega.me', 'Atlantic', 'The Atlantic']
    for game_prefix in pref_list:
        if str.lower(msg_text).startswith(str.lower(game_prefix)):
            logger.debug(f"{user_id} posted a score for {game_prefix}")

            if game_prefix in ['Atlantic', 'The Atlantic', 'atlantic']:
                game_prefix = 'atlantic'

            # send to score scraper
            response = bot_functions.add_score(game_prefix, user_id, msg_text)

            if not response[0]:
                emoji = '❌'

            else:
                if game_prefix in ['worldle', "#Worldle"]:
                    emoji = '🌎'
                elif game_prefix in ['Factle.app']:
                    emoji = '📈'
                elif game_prefix in ['Wordle']:
                    emoji = '📚'
                elif game_prefix in ['boxofficega.me']:
                    emoji = '🎥'
                else:
                    emoji = '✅'

            # finally, react with proper emoji
            await message.add_reaction(emoji)
            if old_msg is not None:
                await old_msg.add_reaction(emoji)

    # run the message check
    await bot.process_commands(message)


# tasks
@tasks.loop(minutes=1)
async def auto_post_the_mini():

    # check current time
    now_ts = datetime.now(pytz.timezone('US/Eastern'))
    now_txt = now_ts.strftime("%Y-%m-%d %H:%M:%S")
    hr = now_ts.hour
    mn = now_ts.minute
    the_time = str(now_ts.hour).zfill(2) + ':' + str(now_ts.minute).zfill(2)

    # get mini_date and cutoff hour
    cutoff_hour = 17 if now_ts.weekday() in [5, 6] else 21
    expiry_time_txt = "6:00PM" if now_ts.weekday() in [5, 6] else "10:00PM"
    if now_ts.hour > cutoff_hour:
        mini_dt = (now_ts + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        mini_dt = now_ts.strftime("%Y-%m-%d")

    # print check
    interval = 5 if local_mode else 30
    if now_ts.minute % interval == 0:
        logger.debug(f'Still connected.')

    # regular run hours of get_mini
    minute_to_run = 55
    if mn == minute_to_run:
        logger.debug(f"Normal time to get the mini (no post)")
        bot_functions.get_mini()

    # check if it's the final hour
    in_final_hour = now_ts.hour == cutoff_hour
    if not in_final_hour:
        return

    # check what post to make at which minute
    warning_minute = 0
    nerds_minute = 59
    is_time_to_post = (now_ts.minute == nerds_minute)

    # get correct channel
    guild = bot.get_guild(nerd_city)
    channel = guild.get_channel(crossword_corner)  # bot_test
    is_time_to_warn = (now_ts.minute == warning_minute)

    # post it
    if is_time_to_post:
        logger.debug("Posting Final Leaderboard")
        end_msg = f"The mini expires at {expiry_time_txt}. Here's the final leaderboard:"
        await channel.send(end_msg)

        # get mini and post image
        img = bot_functions.get_mini()
        await channel.send(file=discord.File(img))

    # send warning
    if is_time_to_warn:
        logger.debug(f"Time for 1-Hour Warning but currently this is disabled")
        await channel.send("The mini expires in 1 hour. If you cared, you would have already done it. I'm going on break.")
        return

        # get missing mini report from sql
        engine = create_engine(sql_addr)
        my_query = """select discord_id_nbr from mini_not_completed"""
        players_missing_mini_score = pd.read_sql(my_query, con=engine)['discord_id_nbr'].tolist()

        # Check if players_missing_mini_score is empty
        if not players_missing_mini_score:
            
            # Celebration message
            celebration_msg = "No warning today. Everyone did the mini..."
            
            # Create an Embed with the GIF URL
            gif_url = "https://media.giphy.com/media/ck5JRWob7folZ7d97I/giphy.gif"
            embed = Embed()
            embed.set_image(url=gif_url)

            # celebrate
            await channel.send(celebration_msg, embed=embed)

        else:

            # create warning message
            warning_msg = inspect.cleandoc(f"""The mini expires at {expiry_time_txt}!
                            The following players have not completed today's puzzle:
                            """)
            for user_id in players_missing_mini_score:
                warning_msg += f"<@{user_id}> "
                warning_msg += "\n"
            warning_msg += "To remove this notification, type '/mini_warning remove' (without the quotes)"

            # warn
            await channel.send(warning_msg)


# command to get other leaderboards (only mini is working right now)
@bot.command(name='get', aliases=['mini', 'wordle', 'factle', 'worldle', 'atlantic', 'boxoffice'])
async def get(ctx, *, time_frame='daily'):
    
    # clarify request
    user_id = ctx.author.name
    time_frame = str.lower(time_frame)
    game_name = ctx.invoked_with

    # print
    logger.debug(f"{user_id} requested {time_frame} {game_name} leaderboard.")

    # only daily available right now
    if time_frame != 'daily':
        return await ctx.channel.send("Sorry, but only daily leaderboards are available right now.")

    # get the data
    try:
        if game_name == 'mini':
            img = bot_functions.get_mini()
            await ctx.channel.send(file=discord.File(img))
        else:
            img = bot_functions.get_leaderboard(game_name)
            await ctx.channel.send(file=discord.File(img))       
    except Exception as e:
        error_message = f"Error getting {game_name} leaderboard: {str(e)}"
        await ctx.channel.send(error_message)

# command to add or remove yourself from mini_warning
@bot.command(name='mini_warning')
async def mini_warning(ctx, *args):
    user_id = str(ctx.author.id)
    action = str.lower(args[0])

    if action not in ['add', 'remove', 'on', 'off']:
        msg = "Must type 'add' or 'remove' after /mini_warning"
        await ctx.channel.send(msg)
        return
    
    # are they turning the warning off or on
    on_or_off = 0 if action in ['remove', 'off'] else 1

    # update sql
    engine = create_engine(sql_addr)
    update_query = """
        update users
        set mini_warning = {on_or_off}
        where discord_id_nbr = {user_id}
    """
    with engine.connect() as connection:
        connection.execute(update_query)
    
    # reply back (happy or sad)
    if on_or_off == 1:
        msg = f"Added you back to the warning message"
        await ctx.channel.send(msg)
    else:
        list_of_gifs = [
            "https://tenor.com/view/boring-unimpressed-meh-really-seriously-gif-16279809",
            "https://giphy.com/gifs/NRXleEopnqL3a",
            "https://giphy.com/gifs/cbc-funny-comedy-3ohhwfwxg4d1h82LxS",
            "https://giphy.com/gifs/oh-yeah-sure-suuure-DFNd1yVyRjmF2",
            "https://giphy.com/gifs/transparent-unimpressed-izPhmitdi9oty",
            "https://giphy.com/gifs/way-morning-dresser-kWp8QC99Z6xFn8bF0v",
            "https://giphy.com/gifs/tjluV258hamaY",
            "https://giphy.com/gifs/high-quality-highqualitygifs-8mdUDkUoAPvEpR8ZIl",
            "https://giphy.com/gifs/theoffice-CuERU1w8npNcP0CpP4"
        ]

        # pick a gif, wait... then react
        reaction_gif = random.choice(list_of_gifs)
        asyncio.sleep(3)  # joke timing
        await ctx.channel.send(reaction_gif)


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
        if message.channel.name not in ["crossword", "crossword-corner", "bot_tester", "bot-test", "game-scores"]:
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
