
## this should run on a completely separate process from the bot
## it should not be linked to Discord at all
## it should check the leaderboard and only write new records
## it should write the records to both a json file and the sql database

import pandas as pd
import datetime
import pytz
import json
import requests
from config import credentials
from bs4 import BeautifulSoup
from bot_functions import get_mini_date
from sql_runners import send_df_to_sql

# save mini to database
def get_mini_to_dataframe():

    # get leaderboard html
    leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
    html = requests.get(leaderboard_url, cookies={'NYT-S': credentials.NYT_COOKIE})

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

    # save scores to json
    with open('mini_history.json', 'r') as f:
        history = json.load(f)


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
