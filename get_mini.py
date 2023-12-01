
## this should run on a completely separate process from the bot
## it should not be linked to Discord at all
## it should write the leaderboard to a file, and only write new records to sql

import pandas as pd
from datetime import datetime
import pytz
import json
import requests
from bs4 import BeautifulSoup
from bot_functions import get_mini_date
from sql_runners import send_df_to_sql
import os
from config import NYT_COOKIE
import asyncio

current_mini_dt = get_mini_date().strftime("%Y-%m-%d")

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

    # get today's mini path
    file_path = f"files/mini/{current_mini_dt}.json"

    # check if file exists, read existing data if it does
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            existing_scores = json.load(f)
    else:
        existing_scores = {}

    # add new scores (if any)
    for player, score in scores.items():
        if player not in existing_scores:
            added_ts = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")
            print(f"{added_ts}: {player} completed the mini in {score}!")
            existing_scores[player] = {
                "time": score,
                "added_ts": added_ts,
                "added_to_sql": False
                }

    # create file if not exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # save updated scores to JSON
    with open(file_path, 'w') as f:
        json.dump(existing_scores, f, indent=4)

    return existing_scores

# save new scores to sql
async def save_new_scores_to_sql(existing_scores):

    # Filter scores that haven't been added to SQL yet
    new_scores = {player: data for player, data in existing_scores.items() if not data['added_to_sql']}
    print(f"There are {len(new_scores)} scores which still need to be added to sql.")

    if new_scores:
        # Prepare DataFrame for SQL
        df = pd.DataFrame(new_scores).transpose().reset_index()
        df.insert(0, 'game_date', current_mini_dt)
        df.drop(columns=['added_to_sql'], inplace=True)
        df.columns = ['game_date', 'player_id', 'game_time', 'added_ts']

        try:
            # Send to SQL
            await send_df_to_sql(df, 'mini_history')

            # If successful, mark these scores as added to SQL
            for player in new_scores.keys():
                print(f"Successfully added {player}'s score to SQL.")
                existing_scores[player]['added_to_sql'] = True

            # Save the updated scores back to JSON
            with open(f"files/mini/{current_mini_dt}.json", 'w') as f:
                json.dump(existing_scores, f, indent=4)

        except Exception as e:
            # Handle the exception (e.g., log it, send an alert, etc.)
            print(f"An error occurred while sending data to SQL: {e}")
            # Do not update the JSON file if there was an error


# get mini
scores_raw = scrape_mini_scores()
print('got scores')

# save new scores to file
scores_json = save_new_scores_to_json(scores_raw)
print('sent to json')

# save new scores to sql
asyncio.run(save_new_scores_to_sql(scores_json))
