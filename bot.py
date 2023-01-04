# main functions and connecting
import os
import socket
import discord
import asyncio
from discord.ext import commands, tasks
from discord.ext.commands import Converter, Context
from dotenv import load_dotenv
import pytz
from datetime import datetime
import bot_functions

# get date and time
now = datetime.now(pytz.timezone('US/Eastern'))
game_date = now.strftime("%Y-%m-%d")
game_time = now.strftime("%Y-%m-%d %H:%M:%S")

# connection details
load_dotenv()
TOKEN = os.getenv('CROSSWORD_BOT')
my_intents = discord.Intents.all()
my_intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=my_intents)


# confirm ready
@bot.event
async def on_ready():
    print(game_time + ': ' + bot.user.name + ' is ready')
    for guild in bot.guilds:
        print(f'Connected to the server: {guild.name} guild id: {guild.id}')
        for channel in guild.channels:
            if channel.name in ['crossword-corner', 'bot-test', 'bot_tester', 'game-scores']:
                print(f'{channel.name} has ID {channel.id}')

    # start this auto-task
    auto_post_the_mini.start()

    # check if local
    local_mode = True if socket.gethostname() == "MJT" else False
    print(f'Variable local_mode is set to: {local_mode}')
    print('')


# command to get other leaderboards
@bot.command(name='get', aliases=['wordle', 'factle', 'worldle', 'atlantic', 'boxoffice', 'mini'])
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


# accept multiple words
class BracketSeparatedWords(Converter):
    async def convert(self, ctx: Context, argument: str) -> list:
        # return argument.split("[")[1].split("]")[0].split()
        argument = argument.strip("[]")
        return argument.split()


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


# message reader
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
    user_id = str(message.author.display_name)

    # print details
    print(f"""*** {msg_time} ... received message in {message.channel.name}""")
    print(f"""*** {user_id} said: {msg_text}""")
    print('')

    # check all potential score posts
    pref_list = ['#Worldle', 'Wordle', 'Factle.app', 'boxofficega.me', 'Atlantic', 'The Atlantic', 'atlantic']
    for game_prefix in pref_list:
        if msg_text.startswith(game_prefix):
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
            print('reacted')

    # run the message check
    await bot.process_commands(message)
    print('')


# command that runs at certain time
@tasks.loop(seconds=60)
async def auto_post_the_mini():

    # check current time
    check_now = datetime.now(pytz.timezone('US/Eastern'))

    # conditions on when to take action
    cond1 = check_now.weekday() >= 5 and check_now.hour == 17  # 5:59PM
    cond2 = check_now.weekday() <= 4 and check_now.hour == 21  # 9:59PM
    test_cond = False
    post_min = 58
    is_end_of_hour = (check_now.minute == post_min)

    # if mini expiring soon...
    if is_end_of_hour and (cond1 or cond2 or test_cond):
        print("Oh snap. Mini expiring soon!")

        # ending message
        msg = "The mini expires in under a minute. Here's the final leaderboard..."
        guild = bot.get_guild(672233217985871908)
        channel = guild.get_channel(806881904073900042)
        await channel.send(msg)

        # get score and post image
        img = bot_functions.get_mini()
        await channel.send(file=discord.File(img))

# run
bot.run(TOKEN)
