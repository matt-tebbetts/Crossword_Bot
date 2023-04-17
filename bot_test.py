import os
import discord
from discord import Intents
from dotenv import load_dotenv
from playlist_creator import create_playlist_from_discord_history
import asyncio

load_dotenv()

DISCORD_TOKEN = os.getenv('CROSSWORD_BOT')
THREAD_ID = 1072246720580296736

intents = Intents.all()
intents.typing = False
intents.presences = False

client = discord.Client(intents=intents)

async def main():
    await client.start(DISCORD_TOKEN)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    # Get the thread using the hardcoded ID
    thread = await client.fetch_channel(THREAD_ID)

    if thread:
        # Call the create_playlist_from_discord_history function
        await create_playlist_from_discord_history(thread, "Test Playlist 2", "Test playlist created from Discord chat history")
        print("Playlist creation process completed.")
    else:
        print(f"Thread with ID '{THREAD_ID}' not found.")

    # Close the Discord connection
    await client.close()

asyncio.run(main())
