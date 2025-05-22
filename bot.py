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
from bot_gpt import fetch_gpt_response

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
if test_mode:
    TOKEN = os.getenv('TEST_BOT')
    print("Running in test mode.")
else:
    TOKEN = os.getenv('CROSSWORD_BOT')
    print("Running in production mode.")
print(f"TOKEN: {TOKEN}")

# discord connection details
my_intents = discord.Intents.all()
my_intents.message_content = True

# bot setup
bot = commands.Bot(command_prefix="/", intents=my_intents, case_insensitive=True)
bot_ready = False

# check chromedriver
# check_chromedriver()

# remove this!!!!
active_channel_names = ["crossword-corner", "game-scores", "bot-test"]

# set game names and prefixes
game_prefixes = ['#Worldle', '#travle', '#travle_usa', '#travle_gbr',
                 'Wordle', 'Factle.app', 'boxofficega.me',
                 'Atlantic', 'Connections', '#Emovi',
                 'Daily Crosswordle', 'TimeGuessr', 'Concludle', 'Actorle', 'Moviedle',
                 'Daily Octordle', 'Daily Sequence Octordle', 'Daily Rescue Octordle']

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
    'octordle_sequence': 'Daily Sequence Octordle',
    'octordle_rescue': 'Daily Rescue Octordle',
    'timeguessr': 'TimeGuessr',
    'concludle': 'Concludle',
    'actorle': 'Actorle',
    'moviedle': 'Moviedle'
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
            'moviedle': '🎬',
            '#emovi': '🎬',
            'connections': '🔠',
            'daily octordle': '🐙', 
            'daily sequence octordle': '🔢',
            'daily rescue octordle': '🚑',
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

# run bot
bot.run(TOKEN)