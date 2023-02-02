# main functions and connecting
import os
import socket
import discord
import asyncio

import random
import pandas as pd
from discord.ext import commands, tasks
from discord.ext.commands import Converter, Context
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta
import inspect
import bot_functions

# connection details
load_dotenv()
TOKEN = os.getenv('CROSSWORD_BOT')
my_intents = discord.Intents.all()
my_intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=my_intents)

# guilds and channel_ids
nerd_city = 672233217985871908
crossword_corner = 806881904073900042
bot_test = 813831098312294490
tebbetts_server = 349702892631883778
game_scores = 1058057309068197989

# set global variables
local_mode = True if socket.gethostname() == "MJT" else False
print(f"local_mode = {local_mode}")

# set file locations
if local_mode:
    img_loc = 'files/images/'
    user_csv = 'files/users.csv'
    mini_csv = 'files/mini_history.csv'
    game_csv = 'files/game_history.csv'
else:
    img_loc = '/home/matttebbetts/projects/Crossword_Bot/files/images/'
    user_csv = '/home/matttebbetts/projects/Crossword_Bot/files/users.csv'
    mini_csv = '/home/matttebbetts/projects/Crossword_Bot/files/mini_history.csv'
    game_csv = '/home/matttebbetts/projects/Crossword_Bot/files/game_history.csv'


# accept multiple words in command arguments/parameters?
class BracketSeparatedWords(Converter):
    async def convert(self, ctx: Context, argument: str) -> list:
        # return argument.split("[")[1].split("]")[0].split()
        argument = argument.strip("[]")
        return argument.split()


# confirm ready
@bot.event
async def on_ready():
    # confirm
    for guild in bot.guilds:
        print(f"Connected to {guild.name}, id: {guild.id}")
        for channel in guild.channels:
            if channel.name in ['crossword-corner', 'game-scores', 'bot-test']:
                print(f"... channel {channel.name} has id: {channel.id}")

        refresh_users = False
        if refresh_users:
            guild_df = pd.DataFrame(columns=['id', 'nick', 'full'])
            for member in guild.members:
                member_id = member.id
                member_nm = member.name
                member_no = member.name + "#" + member.discriminator
                new_row = pd.DataFrame({'id': [member_id], 'nick': [member_nm], 'full': [member_no]})
                guild_df = pd.concat([guild_df, new_row], ignore_index=True)
            guild_df.to_csv(f'files/users_{guild.name}.csv', mode='w', index=False)

    # ready time
    ready_ts = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # start timed tasks
    auto_post_the_mini.start()

    # check if local
    print(f'Local? {local_mode}')
    print('')
    print(f"{ready_ts}: {bot.user.name} is ready")


# messages
@bot.event
async def on_message(message):
    # only comment on certain channel(s)
    if message.channel.name not in ["crossword", "crossword-corner", "bot_tester", "bot-test", "game-scores"]:
        return

    # don't respond to self
    if message.author == bot.user:
        return

    # get message details
    msg_now = datetime.now(pytz.timezone('US/Eastern'))
    msg_time = msg_now.strftime("%Y-%m-%d %H:%M:%S")
    msg_text = str(message.content)
    user_id = message.author.name + "#" + message.author.discriminator #str(message.author.display_name)

    # print details
    print(f"""{msg_time}: received message in {message.channel.name}""")
    print(f"""... {user_id} said: {msg_text}""")
    print('')

    old_msg = None
    # if they wrote "!add" then replace msg_text with the original message
    if msg_text == "!add":
        if message.reference.resolved:
            print('this is a reply to a previous message')
            old_msg = await message.channel.fetch_message(message.reference.message_id)
            print('replacing variables to refer to old message...')
            msg_text = str(old_msg.content)
            user_id = str(old_msg.author.name + "#" + old_msg.author.discriminator)

    # check all potential score posts
    pref_list = ['#Worldle', 'Wordle', 'Factle.app', 'boxofficega.me', 'Atlantic', 'The Atlantic']
    for game_prefix in pref_list:
        if str.lower(msg_text).startswith(str.lower(game_prefix)):
            print('This looks like a game score for: ' + game_prefix)

            if game_prefix in ['Atlantic', 'The Atlantic', 'atlantic']:
                game_prefix = 'atlantic'

            # send to score scraper
            response = bot_functions.add_score(game_prefix, user_id, msg_text)
            print(response)

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

            print('reacted')

    # run the message check
    await bot.process_commands(message)
    print('')


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
    if now_ts.minute in [0]:
        print(f"{now_txt}: Just checking in. Current weekday is {now_ts.weekday()}, mini closes at {cutoff_hour} ({expiry_time_txt})")

    # regular run hours of get_mini
    hours_to_run = [1, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23]
    minute_to_run = 45
    if hr in hours_to_run and mn == minute_to_run:
        print(f"{now_txt}: it's {the_time}, time to run get_mini")
        bot_functions.get_mini()

    # check if it's the final hour
    in_final_hour = now_ts.hour == cutoff_hour
    if not in_final_hour:
        return

    # check what post to make at which minute
    warning_minute = 0
    fam_minute = 50
    nerds_minute = 58

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

    # send warning
    if is_time_to_warn:

        # find today's saved mini detail
        df = pd.read_csv(mini_csv)
        df = df[df['game_date'] == mini_dt]
        df['add_rank'] = df.groupby('player_id')['added_ts'].rank().astype(int)
        df = df[df['add_rank'] == 1]
        print(f'{now_txt}: got most recent mini data...')

        # get users to warn
        users = pd.read_csv(user_csv, converters={'discord_id_nbr': str})
        users = users[(users['give_rank'] == True) & (users['mini_warning'] == True)]
        combined = pd.merge(users, df, how='left', on='player_id')

        # see who hasn't gone yet
        grouped = combined.groupby('discord_id_nbr')['game_time'].count()
        no_mini_list = grouped.loc[grouped == 0].index.tolist()
        print(f"{now_txt}: these users haven't done the mini: {no_mini_list}")

        # send message and tag users
        warning_msg = inspect.cleandoc(f"""The mini expires at {expiry_time_txt}!
                        The following players have not done the mini today:
                        """)
        for user_id in no_mini_list:
            warning_msg += f"<@{user_id}> "
        warning_msg += "\n"
        warning_msg += "To remove this notification, type '/mini_warning remove' (without the quotes)"
        await channel.send(warning_msg)

    # post it
    if is_time_to_post:
        print("auto: yes it's time to post")
        end_msg = f"The mini expires at {expiry_time_txt}. Here's the final leaderboard:"
        await channel.send(end_msg)

        # get score and post image
        img = bot_functions.get_mini(is_family_time)
        await channel.send(file=discord.File(img))


# command to get other leaderboards
@bot.command(name='get', aliases=['mini', 'wordle', 'factle', 'worldle', 'atlantic', 'boxoffice'])
async def get(ctx, *, time_frame='daily'):
    # clarify request
    time_frame = str.lower(time_frame)
    game_name = ctx.invoked_with

    if game_name == 'mini' and time_frame == 'daily':
        disabled = False
    else:
        disabled = True

    # temporarily disable the leaderboard pulls
    if disabled:
        print('leaderboard disabled')
        temp_msg = "Terribly sorry, but this service is currently disabled"
        await ctx.channel.send(temp_msg)
    else:
        print('leaderboard enabled')
        # if daily mini, just run get_mini
        if game_name == 'mini' and time_frame == 'daily':
            my_image = bot_functions.get_mini()
            await ctx.channel.send(file=discord.File(my_image))

        # otherwise, get the requested leaderboard
        else:
            response = bot_functions.get_leaderboard(game_name, time_frame)
            print('response is: ' + str(response))
            if response[0]:
                response_image = response[2]
                print(f"here's the requested leaderboard...")
                await ctx.channel.send(file=discord.File(response_image))
            else:
                print('no records found')
                await ctx.channel.send(f"I have no records for {game_name} today")


# command to add or remove yourself from mini_warning
@bot.command(name='mini_warning')
async def mini_warning(ctx, *args):
    user_id = str(ctx.author.id)
    action = str.lower(args[0])

    if action not in ['add', 'remove', 'on', 'off']:
        msg = "Must type 'add' or 'remove' after /mini_warning"
        await ctx.channel.send(msg)
        return

    action_bool = False if action in ['remove', 'off'] else True

    # open and edit the users file
    users = pd.read_csv(user_csv, converters={'discord_id_nbr': str})
    users.loc[users['discord_id_nbr'] == user_id, 'mini_warning'] = action_bool
    users.to_csv(user_csv, index=False)

    list_of_gifs = [
        "https://tenor.com/view/boring-unimpressed-meh-really-seriously-gif-16279809",
        "https://giphy.com/gifs/NRXleEopnqL3a",
        "https://giphy.com/gifs/eye-roll-ryan-reynolds-ugh-54PaD9dWT0go",
        "https://giphy.com/gifs/iron-man-eye-roll-disgust-qmfpjpAT2fJRK",
        "https://giphy.com/gifs/transparent-unimpressed-izPhmitdi9oty",
        "https://giphy.com/gifs/way-morning-dresser-kWp8QC99Z6xFn8bF0v",
        "https://giphy.com/gifs/tjluV258hamaY",
        "https://giphy.com/gifs/high-quality-highqualitygifs-8mdUDkUoAPvEpR8ZIl"
    ]

    reaction_gif = random.choice(list_of_gifs)

    if action in ['add', 'on']:
        msg = f"Added you back to the warning message"

    if action in ['remove', 'off']:
        msg = reaction_gif

    # reply
    await ctx.channel.send(msg)


# command to draft something # WORK IN PROGRESS
@bot.command(name='draft')
async def draft(ctx, thing: BracketSeparatedWords, category: BracketSeparatedWords):
    # read command details
    user_id = ctx.author.display_name
    confirmation = f"Looks like {user_id} selected '{thing}' from '{category}'"

    list_of_categories = ['A', 'B', 'C']

    if category not in list_of_categories:
        print('invalid category')

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
        print(f"{ctx.author.display_name} tried to call get_history but only Matt can do this")
        return

    # get a get_channel instance
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name == channel_to_find:
                channel_to_scrape = bot.get_channel(channel.id)
                print(f"found channel id: {channel.id} for {channel.name}")

                # find thread
                for thread in channel.threads:
                    if thread.name == thread_to_find:
                        thread_to_scrape = bot.get_channel(thread.id)
                        print(f"found thread id: {thread.id} for {thread.name}")

    # create empty dataframe
    cols = ['msg_id', 'msg_ts', 'char_count', 'word_count', 'uniq_count',
            'swears', 'reacts', 'msg_auth']
    df = pd.DataFrame(columns=cols)
    print('starting with this dataframe')
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
    print('get_history complete')
    print('')

    df.to_csv('test.csv', mode='w', index=False)


# run
bot.run(TOKEN)
