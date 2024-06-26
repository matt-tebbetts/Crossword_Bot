# connections and local python files

# ****************************************************************************** #
# import packages
# ****************************************************************************** #

# connections
import os
import socket
from dotenv import load_dotenv

# local files
from global_functions import *
from bot_functions import *
from bot_camera import dataframe_to_image_dark_mode
from config import test_mode
from bot_sql import send_df_to_sql, get_df_from_sql
from bot_texter import send_sms

# discord
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Converter, Context
from discord import Embed
from discord import app_commands  # trying new method

# data processing
import numpy as np
import pandas as pd
import json
#import openai
#from openai import OpenAI

# timing and scheduling
from datetime import date, datetime, timedelta
import pytz
import asyncio

# ****************************************************************************** #
# set-up
# ****************************************************************************** #

# environment variables
load_dotenv()
TOKEN = os.getenv('MATT_BOT') if test_mode else os.getenv('CROSSWORD_BOT')
if test_mode: print("Running in test mode.")

# discord connection details
my_intents = discord.Intents.all()
my_intents.message_content = True

# bot setup
bot = commands.Bot(command_prefix="/", intents=my_intents, case_insensitive=True)
bot_ready = False

# check chromedriver
check_chromedriver()

# remove this!!!!
active_channel_names = ["crossword-corner", "game-scores", "bot-test"]

# set game names and prefixes
game_prefixes = ['#Worldle', '#travle', '#travle_usa', '#travle_gbr',
                 'Wordle', 'Factle.app', 'boxofficega.me',
                 'Atlantic', 'Connections', '#Emovi',
                 'Daily Crosswordle', 'TimeGuessr', 'Concludle', 'Actorle',
                 'Daily Octordle']

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
    'crosswordle': 'Daily Crosswordle',
    'octordle': 'Daily Octordle',
    'timeguessr': 'TimeGuessr',
    'concludle': 'Concludle',
    'actorle': 'Actorle'
}

# emoji map for confirming game scores (prefix, emoji)
emoji_map = {
            '#worldle': '🌎',
            '#travle': '🌍',
            '#travle_usa': '🇺🇸',
            '#travle_gbr': '🇬🇧',
            'atlantic': '🌊',
            'factle.app': '📈',
            'wordle': '📚',
            'boxofficega.me': '🎥',
            'actorle': '🎭',
            '#emovi': '🎬',
            'connections': '🔠',
            'daily octordle': '🐙', 
            'daily crosswordle': '🧩',
            'timeguessr': '⏱️',
            'concludle': '🏁',
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
    bot_print(f"{bot.user.name} connected to {socket.gethostname()}")

# disconnect
@bot.event
async def on_disconnect():
    bot_print(f"Bot has been disconnected from {socket.gethostname()}")

# startup
@bot.event
async def on_ready():

    # set ready flag
    global bot_ready
    bot_ready = True
    bot_print(f"{bot.user.name} is ready!")

    # get users into json
    get_users(bot)

    # Start timed tasks
    tasks_to_start = [auto_post, check_mini]
    for task in tasks_to_start:
        if not task.is_running():
            task.start()

    return

# read channel messages
@bot.event
async def on_message(message):

    # check if bot is ready
    global bot_ready
    if not bot_ready:
        return

    # ignore self
    if message.author == bot.user:
        return

    # save message into json
    try:
        save_message_detail(message)
    except Exception as e:
        bot_print(f"failed to save message: {e}")

    """
    # adding funny responses here
    if ' twitter' in message.content.lower():
        await message.channel.send("You mean 'X'?")
    """

    # check channel for games
    if message.channel.name not in active_channel_names:
        return

    msg_text = str(message.content)

    # check for game score
    for game_prefix in game_prefixes:

        # if message begins with a game prefix, add the score
        if str.lower(msg_text).startswith(str.lower(game_prefix)):

            # find game name from prefix
            for key, value in game_prefix_dict.items():
                if value.lower() == game_prefix.lower():
                    game_name = key
                    break

            # get message detail
            game_date = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")

            # get discord name
            author = message.author.name
            user_id = author[:-2] if author.endswith("#0") else author

            # get score and bonuses (as dictionary)
            response = await add_score(game_name, game_date, user_id, msg_text)

            # react with proper emoji(s)
            emoji = emoji_map.get(game_prefix.lower(), '✅')
            await message.add_reaction(emoji)

            if response.get('bonuses', {}).get('rainbow_bonus'):
                await message.add_reaction('🌈')
            if response.get('bonuses', {}).get('purple_bonus'):
                await message.add_reaction('🟪')

            # exit the loop since we found the prefix
            break

    # run the message check
    await bot.process_commands(message)

# read channel message edits
@bot.event
async def on_message_edit(before, after):

    try:
        # Call save_message_detail with the edited message
        save_message_detail(after)

    except Exception as e:
        bot_print(f"Failed to update edited message: {e}")


# ****************************************************************************** #
# tasks
# ****************************************************************************** #

# post warning
async def send_mini_warning():

    # find users who have not yet completed the mini
    df = await mini_not_completed()

    if df.empty:
        discord_message = "Wow, everyone has completed the mini!"

    else:
        bot_print(f"Found {len(df)} users who have not completed the mini.")

        # prepare discord tags
        discord_tags = []
        text_count = 0

        # loop through the dataframe
        for index, row in df.iterrows():

            # if they want the text message, send it
            if row['wants_text'] == 1 and row['phone_nbr'] and row['phone_carr_cd']:
                send_sms(
                        name=row['player_name'],
                        number=row['phone_nbr'],
                        carrier=row['phone_carr_cd'],
                        message=f"Hey {row['player_name']}, you can still do today's mini: https://bit.ly/nyt_mini"
                        )
                text_count += 1

            # otherwise, tag them in Discord
            else:
                discord_tag = f"<@{row['discord_id_nbr']}>"
                discord_tags.append(discord_tag)

        # Prepare the final message for the Discord channel
        discord_message = f"Mini expires soon. Texted {text_count}."
        if discord_tags:
            discord_message += " These peeps haven't done the mini yet: " + " ".join(discord_tags)

    # post warning in each active channel for each guild
    for guild in bot.guilds:
        bot_print(f"Posting Mini Warning for {guild.name}")
        for channel in guild.channels:
            if channel.name in active_channel_names and isinstance(channel, discord.TextChannel) and channel.name != 'bot-test':
                await channel.send(discord_message)

# post mini
async def post_mini(guild_name=None, msg=None, final_post=False):
    async with asyncio.Lock():

        # set default message
        if msg is None:
            msg = "Here is the current leaderboard"

        # post in each guild
        for guild in bot.guilds:

            # if guild_name is specified, skip if not the right guild
            if guild_name is not None and guild.name != guild_name:
                continue

            # set mini date
            if final_post:
                min_date, max_date = get_date(), get_date()
            else:
                min_date, max_date = get_mini_date(), get_mini_date()

            # get leaderboard
            img = await get_leaderboard(guild_id=str(guild.id), game_name='mini',
                                        min_date=min_date, max_date=max_date)

            for channel in guild.channels:

                # only post in certain channels
                cond1 = channel.name in active_channel_names
                cond2 = isinstance(channel, discord.TextChannel)
                cond3 = channel.name != 'bot-test'

                # post
                if cond1 and cond2 and cond3:
                    await channel.send(msg)
                    await channel.send(file=discord.File(img))

            if guild_name is not None:
                break

# ****************************************************************************** #
# timers for the tasks
# ****************************************************************************** #

# this function runs every minute to see if we should post the mini leaderboard
@tasks.loop(minutes=1)
async def auto_post():

    # check if it's time for any auto-post
    now = get_now()
    post_hour = get_cutoff_hour()
    warn_hour = post_hour - 2

    # for final time
    if now.hour == post_hour and now.minute == 0:
        bot_print("Time to post final!")
        await post_mini(msg="Here's the final leaderboard", final_post=True) # all guilds
        return

    # for warning time
    elif now.hour == warn_hour and now.minute == 0:
        bot_print("Time to warn!")
        await send_mini_warning()
        await post_mini()
        return

    else:
        return

@tasks.loop(seconds=5)
async def check_mini():

    # don't run this in first five minutes after new mini
    now = get_now()
    if now.hour == get_cutoff_hour() and now.minute < 5:
        return

    # check for leader changes
    try:
        guild_differences = await check_mini_leaders()

    except Exception as e:
        bot_print(f"Error in check_mini part 1: {e}")
        return

    try:
        for guild_name, has_new_leader in guild_differences.items():
            if has_new_leader:
                message = f"New mini leader for {guild_name}!"
                bot_print(message)
                await post_mini(guild_name=guild_name, msg=message)

        # reset after cutoff_hour
        now = get_now()
        if now.hour == get_cutoff_hour() and now.minute == 0 and now.second < 10:
            for guild in bot.guilds:
                guild_name = guild.name
                leader_filepath = f"files/guilds/{guild_name}/leaders.json"
                write_json(leader_filepath, []) # makes it an empty list

    except Exception as e:
        bot_print(f"Error in check_mini part 2: {e}")

# ****************************************************************************** #
# commands (only 2 right now: /get and /rescan)
# /get can be replaced by any of the game names
# ****************************************************************************** #

from openai import AsyncOpenAI

# chat gpt
gpt_key = os.getenv('OPENAI_API_KEY')
openai_client = AsyncOpenAI(api_key=gpt_key)

# gpt command
@bot.command(name='gpt')
async def fetch_gpt_response(ctx, *, query: str):

    # return confirmation message then continue with the process
    await ctx.send(f"Okay, just a sec...")

    # only allow svendiamond to use this command
    is_allowed_author = ctx.author.id == 340940380927295491 or ctx.author.id == 163849350827606016

    if not is_allowed_author:
        return await ctx.send("Sorry, this feature is locked for now.")
    
    try:

        print(f"User requested GPT response to this prompt: {query}")

        # estimate tokens
        est_tokens = len(query) / 4
        est_cost = round(est_tokens * 0.0000005, 2)
        if est_cost < 0.01:
            est_cost = "under a penny"
        print(f"Estimated tokens: {est_tokens}, Estimated cost: {est_cost}")

        # data input
        sql_query = """
        SELECT
            game_name,
            game_date,
            player_name,
            game_score,
            game_rank,
            seconds as score_as_integer
        FROM game_view
        WHERE guild_nm = 'global'
        and game_date >= '2024-01-01'
        """

        # get the game stats in text format
        df = await get_df_from_sql(query=sql_query, params=None)
        analysis_data = df.to_csv(index=False, header=True)

        # read the /gpt command and the game data
        analysis_request = ctx.message.content

        # full input should be the analysis request followed by an explanation that next is the game data...
        full_input = f"Briefly and succinctly answer the analysis request based on the game data.\nAnalysis Request:\n{analysis_request}\n\nGame Data:\n{analysis_data}"

        # tell the model to creatively summarize the game data
        gpt_role_description = """
        Imagine you are a highly skilled senior data analyst with expertise in analyzing data for a leading gaming analytics firm. Your role involves delving into datasets to uncover meaningful insights, trends, and patterns that can help both gamers and developers understand gaming performance on a deeper level.

        When responding to queries, your goal is to provide comprehensive insights, however you must keep your responses short and sweet. No response should be more than 2000 characters in total, but ideally your response should use bullet points and keep things straight to the point.

        Remember, your responses must be brief enough to fit within a short message, yet rich with information and analysis. Your expertise should illuminate aspects of the data that might not be obvious, providing both direct answers and broader insights that can inform strategies, improve player experiences, and spark curiosity.
        """

        gpt_model = 'gpt-4-turbo' # gpt-3.5-turbo-0125

        # ask GPT
        response = await openai_client.chat.completions.create(

            # configuration
            model=gpt_model,
            messages=[
                {"role": "system", "content": gpt_role_description},
                {"role": "user", "content": full_input}
            ],
            max_tokens=1000
        )
 
        # Sending the response back to the Discord channel
        await ctx.send(response.choices[0].message.content)

    except Exception as e:

        error_message = str(e)
        if "token limit exceeded" in error_message.lower():
            custom_message = "Error: Token limit exceeded. Please try a shorter query."
        else:
            custom_message = f"Error: {error_message}"

        await ctx.send(custom_message)

# get leaderboards
@bot.command(name='get', aliases=list_of_game_names)
async def get(ctx, *args):

    # check user and game
    user_nm = None
    game_name = ctx.invoked_with.strip()

    # set defaults
    guild_id = None
    time_frame = None
    list_of_valid_time_frames = ['today', 'yesterday', 'this week', 'last week', 'this month', 'last month', 'this year', 'last year', 'all time']

    # check arguments
    for i in range(len(args)):
        arg = args[i]
        joined_arg = ' '.join(args[i:i+2])
    
        # guild check
        if arg.lower() == "global":
            guild_id = guild_nm = "global"
    
        # time frame check
        if joined_arg.lower() in list_of_valid_time_frames:
            time_frame = joined_arg.lower()

        # user check
        if arg.startswith('<@') and arg.endswith('>'):
            user_id = arg[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
            user = ctx.guild.get_member(int(user_id))
            if user:
                user_nm = user.name if user.discriminator == "0" else user.name + "#" + user.discriminator

        # summary check
        if arg.lower() == "summary":

            # only "actorle" has a summary option for now so
            if game_name != "actorle":
                return await ctx.channel.send("Sorry, the summary is only currently available for Actorle.")
                
            # get the summary
            img = await get_actorle_summary()
            return await ctx.channel.send(file=discord.File(img))
            

    # logic for no guild provided
    if guild_id is None:
        guild_id = str(ctx.guild.id)
        guild_nm = ctx.guild.name

    # logic for no time_frame provided
    if time_frame is None:
        if ctx.invoked_with == 'mini':
            time_frame = get_mini_date().strftime("%Y-%m-%d")
        else:
            time_frame = 'today'

    # if no user provided
    if user_nm is None:
        user_nm = ctx.author.name if ctx.author.discriminator == "0" else ctx.author.name + "#" + ctx.author.discriminator
    
    # print
    bot_print(f"Leaderboard Request: {guild_nm} user {user_nm} requested leaderboard for {game_name} for {time_frame}.")

    # get the min_date and max_date based on the user's input
    date_range = get_date_range(time_frame)
    if date_range is None:
        return await ctx.channel.send("""
            Invalid date range or format.
            Please try again with a valid date range or keyword
            (e.g., 'yesterday', 'last week', 'this month', etc.).")
            """)
    min_date, max_date = date_range

    # get the leaderboard
    try:
        img = await get_leaderboard(guild_id, game_name, min_date, max_date, user_nm)

        # send image of leaderboard to discord
        await ctx.channel.send(file=discord.File(img))

    # report errors
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

    # start dataframe to keep track  of re-added scores
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
                game_date = message.created_at.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")
                # find game name from prefix
                for key, value in game_prefix_dict.items():
                    if value.lower() == game_prefix.lower():
                        game_name = key
                        break
                
                # get discord name
                author = message.author.name
                user_id = author[:-2] if author.endswith("#0") else author

                bot_print(f"Found {user_id}'s {game_prefix} score from {game_date}")

                # send to score scraper
                response = await add_score(game_name, game_date, user_id, msg_text)

                # react with proper emoji
                emoji = '❌' if not response[0] else emoji_map.get(game_prefix.lower(), '✅')
                await message.add_reaction(emoji)

                # add to counter
                condition = (df['Player'] == user_id) & (df['Game Name'] == game_name) & (df['Game Date'] == game_date)

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