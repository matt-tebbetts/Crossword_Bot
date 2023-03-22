# main functions and connecting
import os
from dotenv import load_dotenv
import socket
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Converter, Context
from discord import Embed
import asyncio
import time
import random
import pandas as pd
import pytz
from datetime import datetime, timedelta
import inspect
import bot_functions
import logging
from sqlalchemy import create_engine

### ------------ logging ------------ ###

# Create a formatter that includes a timestamp
formatter = logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# Create a logger and set its log level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler and set its log level and formatter
file_handler = logging.FileHandler('files/bot.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

### ------------ logging ------------ ###

# connection details
load_dotenv()
TOKEN = os.getenv('CROSSWORD_BOT')
my_intents = discord.Intents.all()
my_intents.message_content = True
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

# set global variables
local_mode = True if socket.gethostname() == "MJT" else False
logger.debug(f"Started on: {socket.gethostname()}")

# set file locations
img_loc = 'files/images/'


# accept multiple words in command arguments/parameters?
class BracketSeparatedWords(Converter):
    async def convert(self, ctx: Context, argument: str) -> list:
        # return argument.split("[")[1].split("]")[0].split()
        argument = argument.strip("[]")
        return argument.split()

# if disconnect
@bot.event
async def on_disconnect():
    logger.warning("Bot has been disconnected.")

# startup
@bot.event
async def on_ready():

    # check connected guilds and channels
    for guild in bot.guilds:
        logger.debug(f"Connected to {guild.name} ({guild.id})")
        for channel in guild.channels:
            if channel.name in ['crossword-corner', 'game-scores', 'bot-test']:
                logger.debug(f"Active channels: {channel.name} ({channel.id})")

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
    fam_minute = 45
    nerds_minute = 59

    is_time_to_post = (now_ts.minute == nerds_minute or now_ts.minute == fam_minute)
    is_family_time = (now_ts.minute == fam_minute)

    # get correct channel
    if is_family_time:
        guild = bot.get_guild(tebbetts_server)
        channel = guild.get_channel(game_scores)
        is_time_to_warn = False
    else:
        guild = bot.get_guild(nerd_city)
        channel = guild.get_channel(crossword_corner)  # bot_test
        is_time_to_warn = (now_ts.minute == warning_minute)

    # post it
    if is_time_to_post:
        logger.debug("Posting Final Leaderboard")
        end_msg = f"The mini expires at {expiry_time_txt}. Here's the final leaderboard:"
        await channel.send(end_msg)

        # get mini and post image
        img = bot_functions.get_mini(is_family_time)
        await channel.send(file=discord.File(img))

    # send warning
    if is_time_to_warn:
        logger.debug(f"Posting 1-Hour Warning")

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
    time_frame = str.lower(time_frame)
    game_name = ctx.invoked_with

    # only command that works right now is "mini" otherwise this is disabled
    if game_name == 'mini' and time_frame == 'daily':
        disabled = False
    else:
        disabled = True

    # temporarily disable the leaderboard pulls
    if disabled:
        logger.debug('leaderboard disabled')
        temp_msg = "Terribly sorry, but this service is currently disabled"
        await ctx.channel.send(temp_msg)
    else:
        logger.debug('leaderboard enabled')
        my_image = bot_functions.get_mini()
        await ctx.channel.send(file=discord.File(my_image))


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


##
## incomplete commands below
##

# command to draft something # WORK IN PROGRESS
@bot.command(name='draft')
async def draft(ctx, thing: BracketSeparatedWords, category: BracketSeparatedWords):
    # read command details
    user_id = ctx.author.display_name
    confirmation = f"Looks like {user_id} selected '{thing}' from '{category}'"

    list_of_categories = ['A', 'B', 'C']

    if category not in list_of_categories:
        logger.debug('invalid category')

    # send message
    await ctx.channel.send(confirmation)


# command to get history # WORK IN PROGRESS
@bot.command(name='get_history')
async def get_history(ctx):
    # set limits
    days = 30
    msgs = 10000
    min_date = datetime.utcnow() - timedelta(days=days)

    # find channel to scrape
    channel_to_find = "things-we-watch"
    thread_to_find = "Libertine Draft"

    if str.lower(ctx.author.display_name) != "matt":
        logger.debug(f"{ctx.author.display_name} tried to call get_history but only Matt can do this")
        return

    # get a get_channel instance
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name == channel_to_find:
                channel_to_scrape = bot.get_channel(channel.id)
                logger.debug(f"found channel id: {channel.id} for {channel.name}")

                # find thread
                for thread in channel.threads:
                    if thread.name == thread_to_find:
                        thread_to_scrape = bot.get_channel(thread.id)
                        logger.debug(f"found thread id: {thread.id} for {thread.name}")

    # create empty dataframe
    cols = ['msg_id', 'msg_ts', 'char_count', 'word_count', 'uniq_count',
            'swears', 'reacts', 'msg_auth']
    df = pd.DataFrame(columns=cols)
    logger.debug('starting with this dataframe')
    bot_functions.tab_df(df)

    # check each message
    msg_id = 0
    async for message in thread_to_scrape.history(limit=msgs, oldest_first=True, after=min_date):

        # msg_hdr
        msg_id += 1
        msg_ts = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        msg_auth = str(message.author.display_name)
        msg_char_count = len(message.content)
        msg_word_count = len(message.content.split())

        # msg_dtl
        msg_uniq_words = set(message.content.split())
        msg_uniq_count = len(msg_uniq_words)

        # check for curse words
        swears = 0
        swear_words = ['fuck', 'shit', 'damn', 'dammit', 'fucking', 'shitting', 'asshole', 'assholes', 'bitch']
        for word in message.content.split():
            if word in swear_words:
                swears += 1

        # check for emojis
        emojis = 0
        reacts = 0
        # emojis_used = []
        if message.reactions:
            for reaction in message.reactions:
                # emojis_used += reaction.emoji.name
                reacts += 1

        # put it all in a row
        my_data = [msg_id, msg_ts, msg_char_count, msg_word_count, msg_uniq_count, swears, reacts, msg_auth]

        # append new row to dataframe here??
        df = pd.concat([df, pd.DataFrame([my_data], columns=cols)], ignore_index=True)

    bot_functions.tab_df(df)

    # done
    df.to_csv('test.csv', mode='w', index=False)

##
## incomplete commands above
##

# run bot
bot.run(TOKEN)
