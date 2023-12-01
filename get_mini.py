
## this should run on a completely separate process from the bot
## it should not be linked to Discord at all
## it should write the leaderboard to a file, and only write new records to sql

import pandas as pd
import datetime
import pytz
import json
import requests
from bs4 import BeautifulSoup
from bot_functions import get_mini_date
from sql_runners import send_df_to_sql
import os
from config import NYT_COOKIE

# scrape mini scores
def scrape_mini_scores():

    # get leaderboard html
    leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
    html = requests.get(leaderboard_url, cookies={'NYT-S': NYT_COOKIE})

    # find scores in the html
    soup = BeautifulSoup(html.text, features='lxml')
    divs = soup.find_all("div", class_='lbd-score')
    scores = {}
    for div in divs:
        name = div.find("p", class_='lbd-score__name').getText().strip().replace(' (you)', '')
        time_div = div.find("p", class_='lbd-score__time')
        if time_div:
            time = time_div.getText()
            if time != '--':
                scores[name] = time

    return scores

# save mini scores to file
def save_new_scores_to_json(scores):

    # get current mini date
    current_mini_dt = datetime.now().strftime("%Y-%m-%d")

    # set file path
    file_path = f"files/mini/{current_mini_dt}.json"

    # check if file exists, read existing data if it does
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            existing_scores = json.load(f)
    else:
        existing_scores = {}

    # update existing scores with new scores, only if they are not already present
    for player, score in scores.items():
        if player not in existing_scores:
            existing_scores[player] = score

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save updated scores to JSON
    with open(file_path, 'w') as f:
        json.dump(existing_scores, f)



x = scrape_mini_scores()
print(x)






"""
# check for new scores and add them to sql database
def add_new_scores_to_sql():




    # put scores into df
    df = pd.DataFrame(scores.items(), columns=['player_id', 'game_time'])
    df['player_id'] = df['player_id'].str.lower()
    df.insert(0, 'game_date', get_mini_date().strftime("%Y-%m-%d"))
    df['added_ts'] = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # send to database
    if len(df) == 0:
        return [False, "Nobody did the mini yet"]
    else:
        try:
            send_df_to_sql(df, 'mini_history', if_exists='append')
            return [True, "Got mini and saved to database"]
        except Exception as e:
            return [False, f"Error saving mini to database: {e}"]
"""