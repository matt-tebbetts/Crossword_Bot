# test.py
import bot
import bot_functions
import asyncio
import discord
import os
from types import SimpleNamespace

async def main():
    # Create a mock context object with the required attributes
    ctx = SimpleNamespace()
    ctx.author = SimpleNamespace(name="JohnDoe", discriminator="1234")
    ctx.guild = SimpleNamespace(id=672233217985871908, name="ExampleGuild")
    ctx.invoked_with = "mini"

    # Set the time_frame for the /mini command
    time_frame = "today"

    # Call the get function
    await bot.get(ctx, time_frame=time_frame)

    # Save the output image to a file
    image_path = os.path.join("files", "images", "leaderboard.png")
    img = bot_functions.get_leaderboard(ctx.guild.id, ctx.invoked_with, min_date, max_date, None)
    img.save(image_path)
    print(f"Image saved to {image_path}")

# Run the main function using asyncio
asyncio.run(main())
