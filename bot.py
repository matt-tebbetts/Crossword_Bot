# main functions and connecting
import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# for getting date and time
import pytz
from datetime import datetime

# custom
import bot_functions

# get date and time
now = datetime.now(pytz.timezone('US/Eastern'))
game_date = now.strftime("%Y-%m-%d")
game_time = now.strftime("%Y-%m-%d %H:%M:%S")

# connect to discord
load_dotenv()
TOKEN = os.getenv('TEBBETTS_BOT')
my_intents = discord.Intents.all()
my_intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=my_intents)

# confirm ready
@bot.event
async def on_ready():
    print(game_time + ': ' + bot.user.name + ' is ready')
    print('')

## ************************************************************** ##
## scheduled actions
## ************************************************************** ##


## ************************************************************** ##
## commands
## ************************************************************** ##
# command to get today's mini
@bot.command(name='mini')
async def mini(ctx):
    my_image = bot_functions.get_mini()
    await ctx.channel.send(file=discord.File(my_image))

# command to get other leaderboards
@bot.command(name='wordle')
async def wordle(ctx, time_frame='daily'):
    time_frame = str.lower(time_frame.strip())

    # this should return a list object
    response = bot_functions.get_leaderboard('wordle', time_frame)
    print('response is: ' + str(response))

    if response[0]:
        response_image = f'files/{time_frame.lower()}/Wordle.png'
        print(f"here's the {time_frame} leaderboard")
        await ctx.channel.send(file=discord.File(response_image))
    else:
        print('generic response')
        await ctx.channel.send("I have no records for Wordle today")


@bot.command(name='factle')
async def wordle(ctx):
    bot_functions.get_leaderboard('factle')
    response_image = 'files/weekly/Factle.png'
    await ctx.channel.send(file=discord.File(response_image))

@bot.command(name='worldle')
async def worldle(ctx):
    bot_functions.get_leaderboard('worldle')
    response_image = 'files/weekly/Worldle.png'
    await ctx.channel.send(file=discord.File(response_image))

# command to draft something
@bot.command(name='draft')
async def draft(ctx, movie_name):
    await ctx.channel.send(f'drafting {movie_name}')

# message reader
@bot.event
async def on_message(message):

    # only comment on certain channel(s)
    if message.channel.name not in ["crossword", "bot_tester"]:
        return

    # don't respond to self
    if message.author == bot.user:
        return

    # get message details
    msg_text = str(message.content)
    user_id = str(message.author.display_name)

    print(f"""*** {game_time} ... received message in {message.channel.name}""")
    print(f"""*** {user_id} said: {msg_text}""")
    print('')

    # check all potential score posts
    pref_list = ['#Worldle', 'Wordle', 'Factle.app', 'boxofficega.me']
    for game_id in pref_list:
        if msg_text.startswith(game_id):
            print('This looks like a game score for: ' + game_id)

            # send to score scraper
            response = bot_functions.add_score(game_id, user_id, msg_text)
            print(response)

            # send message back?
            await message.channel.send(response)

    # this just tells the message reader to run (don't touch)
    await bot.process_commands(message)
    print('')

# run bot
bot.run(TOKEN)
