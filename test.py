import bot_functions
import os
from PIL import Image

game_name = 'mini'
time_frame = 'this year'


# get the min_date and max_date based on the user's input
date_range = bot_functions.get_date_range(time_frame)
min_date, max_date = date_range

# get image
img_path = bot_functions.get_leaderboard(
                                        guild_id="672233217985871908",
                                        game_name=game_name,
                                        min_date=min_date,
                                        max_date=max_date)


Image.open(img_path).show()