# main functions and connecting
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# for getting date and time
import pytz
from datetime import datetime

# custom
import score_scraper

# get date and time
now = datetime.now(pytz.timezone('US/Eastern'))
game_date = now.strftime("%Y-%m-%d")
game_time = now.strftime("%Y-%m-%d %H:%M:%S")

# connect to discord
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
my_intents = discord.Intents.all()
my_intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=my_intents)

# confirm ready
@bot.event
async def on_ready():
    print(game_time + ': ' + bot.user.name + ' is ready')
    print('')

# command to get today's mini
@bot.command(name='mini')
async def mini(ctx):
    my_image = '/home/matttebbetts/mini_screenshots/latest.png'
    await ctx.channel.send(file=discord.File(my_image))

# command for getting leaderboard image?
@bot.command(name='ranks')
async def ranks(ctx):
    await ctx.channel.send('Sorry, can''t do that yet. I''m just a big dumb bot.')

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
    user_id = str(message.author.name)
    user_nickname = message.author.display_name
    #print(user_nickname)

    print(f"""*** {game_time} ... received message in {message.channel.name}""")
    print(f"""*** {user_nickname} said:""")
    print('')
    print(f"""{msg_text}""")
    print('')

    # check all potential score posts
    pref_list = ['#Worldle', 'Wordle', 'Factle.app', 'boxofficega.me']

    for game_id in pref_list:
        if msg_text.startswith(game_id):
            print('This looks like a game score for: ' + game_id)

            # send to score scraper
            response = score_scraper.add_score(game_id, user_id, msg_text)
            print(response)

            # send message back?
            await message.channel.send(response)

    # this tells it to process this command
    await bot.process_commands(message)
    print('')

# run bot
bot.run(TOKEN)
