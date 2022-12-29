# main functions and connecting
import os
import socket
import discord
from discord.ext import commands
from dotenv import load_dotenv
import pytz
from datetime import datetime
import bot_functions

# get date and time
now = datetime.now(pytz.timezone('US/Eastern'))
game_date = now.strftime("%Y-%m-%d")
game_time = now.strftime("%Y-%m-%d %H:%M:%S")

# connect to discord
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
        print(f'Connected to the server: {guild.name}')
    
    # check if local
    local_mode = True if socket.gethostname() == "MJT" else False
    print(f'Variable local_mode is set to: {local_mode}')
    print('')


# command to get today's mini
@bot.command(name='mini')
async def mini(ctx):
    my_image = bot_functions.get_mini()
    await ctx.channel.send(file=discord.File(my_image))


# command to get other leaderboards
@bot.command(name='get', aliases=['wordle', 'factle', 'worldle'])
async def get(ctx, time_frame='daily'):

    # figure out which game it is
    time_frame = str.lower(time_frame.strip())
    game_name = ctx.invoked_with

    # get the leaderboard
    response = bot_functions.get_leaderboard(game_name, time_frame)
    print('response is: ' + str(response))

    if response[0]:
        response_image = f'files/images/{time_frame.lower()}_{game_name}.png'
        print(f"here's the {time_frame} leaderboard")
        await ctx.channel.send(file=discord.File(response_image))
    else:
        print('no records found')
        await ctx.channel.send(f"I have no records for {game_name} today")


# command to draft something
@bot.command(name='draft')
async def draft(ctx, movie_name):
    await ctx.channel.send(f'drafting {movie_name}')


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

            # react with proper emoji
            await message.add_reaction(emoji)


    # run the message check
    await bot.process_commands(message)
    print('')


# run bot
bot.run(TOKEN)
