import pandas as pd
import numpy as np
from tabulate import tabulate
import bot_camera

df = pd.read_csv('files/mini_dark.csv')

print(tabulate(df, headers='keys', tablefmt='psql'))

bot_camera.dataframe_to_image_dark_mode(df)