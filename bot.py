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

# Disable all commands except score saving
bot.remove_command('help')  # Remove default help command

# Remove all other commands
for command in list(bot.commands):
    bot.remove_command(command.name)

# check chromedriver
# check_chromedriver()

# remove this!!!!
active_channel_names = ["crossword-corner", "game-scores", "bot-test"]

def load_games_config():
    """Load games configuration from JSON file"""
    with open('files/config/games.json', 'r') as f:
        games_config = json.load(f)
    
    # Build game_prefixes list
    game_prefixes = []
    game_prefix_dict = {}
    emoji_map = {}
    
    for game_name, game_data in games_config.items():
        if 'prefix' in game_data:
            game_prefixes.append(game_data['prefix'])
            game_prefix_dict[game_name] = game_data['prefix']
            emoji_map[game_data['prefix'].lower()] = game_data.get('emoji', '✅')
    
    # Sort prefixes by length to prevent prefix conflicts
    game_prefixes.sort(key=len, reverse=True)
    
    return game_prefixes, game_prefix_dict, emoji_map, games_config

# Load game configuration
game_prefixes, game_prefix_dict, emoji_map, games_config = load_games_config()

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
    
    # No need to start timed tasks since we're only saving scores
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

            # Add bonus emojis if available
            if game_name in games_config and 'bonus_emojis' in games_config[game_name]:
                bonuses = response.get('bonuses', {})
                for bonus_key, bonus_emoji in games_config[game_name]['bonus_emojis'].items():
                    if bonuses.get(bonus_key):
                        await message.add_reaction(bonus_emoji)

            # exit the loop since we found the prefix
            break

# read channel message edits
@bot.event
async def on_message_edit(before, after):
    # Save edited message
    try:
        save_message_detail(after)
    except Exception as e:
        bot_print(f"failed to save edited message: {e}")

# ****************************************************************************** #
# commands
# ****************************************************************************** #

# run bot
bot.run(TOKEN)