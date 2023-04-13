import os
import socket
import requests
import pandas as pd
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import numpy as np
import matplotlib.pyplot as plt
import six
import pytz
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, text
import logging
import bot_camera
from config import credentials, sql_addr

# set up logging?
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# get secrets
load_dotenv()
NYT_COOKIE = os.getenv('NYT_COOKIE')

# find main channel id for each guild
def get_bot_channels():
    engine = create_engine(sql_addr)
    connection = engine.connect()
    query = f"""
        SELECT guild_id, channel_id, guild_channel_category
        FROM discord_connections
        WHERE guild_channel_category = 'main'
    """
    result = connection.execute(text(query))
    rows = result.fetchall()
    connection.close()

    bot_channels = {}
    for row in rows:
        row_dict = dict(zip(result.keys(), row)) # convert row to dict
        bot_channels[row_dict["guild_id"]] = {
            "channel_id": row_dict["channel_id"],
            "channel_id_int": int(row_dict["channel_id"]),
        }

    return bot_channels

# get mini date
def get_mini_date():
    now = datetime.now(pytz.timezone('US/Eastern'))
    cutoff_hour = 17 if now.weekday() in [5, 6] else 21
    if now.hour > cutoff_hour:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return now.strftime("%Y-%m-%d")

# save mini to database
def get_mini():

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

    # put scores into df
    df = pd.DataFrame(scores.items(), columns=['player_id', 'game_time'])
    df['player_id'] = df['player_id'].str.lower()
    df.insert(0, 'game_date', get_mini_date())
    df['added_ts'] = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # send to database
    if len(df) == 0:
        return [False, "Nobody did the mini yet"]
    else:
        engine = create_engine(sql_addr)
        df.to_sql(name='mini_history', con=engine, if_exists='append', index=False)
        return [True, "Got mini and saved to database"]

# translate date range based on text
def get_date_range(user_input):
    today = datetime.now(pytz.timezone('US/Eastern')).date()

    if user_input == 'today':
        min_date = max_date = today
    elif user_input == 'yesterday':
        min_date = max_date = today - timedelta(days=1)
    elif user_input == 'last week':
        min_date = today - timedelta(days=today.weekday(), weeks=1)
        max_date = min_date + timedelta(days=6)
    elif user_input == 'this week':
        min_date = today - timedelta(days=today.weekday())
        max_date = min_date + timedelta(days=6)
    elif user_input == 'this month':
        min_date = today.replace(day=1)
        max_date = (min_date.replace(month=min_date.month % 12 + 1) - timedelta(days=1))
    elif user_input == 'last month':
        min_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        max_date = (min_date.replace(month=min_date.month % 12 + 1) - timedelta(days=1))
    elif user_input == 'this year':
        min_date = today.replace(month=1, day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        max_date = next_month - timedelta(days=next_month.day)
    elif user_input == 'last year':
        min_date = today.replace(year=today.year - 1, month=1, day=1)
        max_date = today.replace(year=today.year - 1, month=12, day=31)
    elif user_input == 'all time':
        min_date = date.min
        max_date = date.max
    else:
        try:
            # Try to parse user input as a date range in format "YYYY-MM-DD:YYYY-MM-DD"
            min_date, max_date = [datetime.strptime(d.strip(), "%Y-%m-%d").date() for d in user_input.split(':')]
        except ValueError:
            # If input is invalid, return None
            return None

    return min_date, max_date

# returns image location of leaderboard
def get_leaderboard(guild_id, game_name, min_date=None, max_date=None):
    engine = create_engine(sql_addr)
    connection = engine.connect()
    logger.debug(f'Connected to database using {sql_addr}')
    today = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")

    # if no date range, use default
    if min_date is None and max_date is None:
        min_date, max_date = today, today

    # get date range to print on subtitle
    if min_date == max_date:
        title_date = get_mini_date() if game_name == 'mini' else min_date.strftime("%Y-%m-%d")
    else:
        title_date = f"{min_date} - {max_date}"
    
    # decide which query to run
    if min_date == max_date:
        
        # single date
        cols = ['rank', 'player', 'score', 'points']
        query = f"""
            SELECT 
                game_rank,
                player_name,
                game_score,
                points
            FROM game_view
            WHERE guild_id = :guild_id
            AND game_name = :game_name 
            AND game_date BETWEEN :min_date AND :max_date
            ORDER BY game_rank;
        """
    else:
        
        # date range
        cols = ['rank', 'player', 'best', 'points']
        query = f"""
        SELECT
            DENSE_RANK() OVER(ORDER BY X.points DESC) as game_rank,
            X.*
        FROM
                (
                SELECT 
                    player_name,
                    min(game_score) as best_score,
                    sum(points) as points
                FROM game_view
                WHERE guild_id = :guild_id
                AND game_name = :game_name 
                AND game_date BETWEEN :min_date AND :max_date
                GROUP BY 1
                ) X
        """
    
    # run the query
    result = connection.execute(text(query), 
                                            {"guild_id": guild_id, 
                                            "game_name": game_name, 
                                            "min_date": min_date, 
                                            "max_date": max_date})
    rows = result.fetchall()
    connection.close()
    df = pd.DataFrame(rows, columns=cols)

    # create image
    my_title = f"{game_name.capitalize()}"
    my_subtitle = f"{title_date}"
    img = bot_camera.dataframe_to_image_dark_mode(df, img_title=my_title, img_subtitle=my_subtitle)
    logger.debug(f'Created image of dataframe for {game_name} leaderboard.')
    return img

# add discord scores to database when people paste them to discord chat
def add_score(game_prefix, game_date, discord_id, msg_txt):

    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    added_ts = now.strftime("%Y-%m-%d %H:%M:%S")

    # set these up
    game_name = None
    game_score = None
    game_dtl = None
    metric_01 = None
    metric_02 = None
    metric_03 = None

    if game_prefix == "#Worldle":
        game_name = "worldle"
        game_score = msg_txt[14:17]

    if game_prefix == "Wordle":
        game_name = "wordle"

        # find position slash for the score
        found_score = msg_txt.find('/')
        if found_score == -1:
            msg_back = [False, 'Invalid format']
            return msg_back
        else:
            game_score = msg_txt[11:14]
            metric_02 = 1 if game_score[0] != 'X' else 0

    if game_prefix == "Factle.app":
        game_name = "factle"
        game_score = msg_txt[14:17]
        game_dtl = msg_txt.splitlines()[1]
        lines = msg_txt.split('\n')

        # find green frogs
        g1, g2, g3, g4, g5 = 0, 0, 0, 0, 0
        for line in lines[2:]:
            if line[0] == '🐸':
                g1 = 1
            if line[1] == '🐸':
                g2 = 1
            if line[2] == '🐸':
                g3 = 1
            if line[3] == '🐸':
                g4 = 1
            if line[4] == '🐸':
                g5 = 1
        metric_03 = g1 + g2 + g3 + g4 + g5
        logger.debug(f"got {metric_03} green frogs")

        # get top X% denoting a win
        final_line = lines[-1]
        if "Top" in final_line:
            metric_01 = final_line[4:]
            metric_02 = 1
        else:
            game_score = 'X/5'
            metric_02 = 0

    if game_prefix == 'boxofficega.me':
        game_name = 'boxoffice'
        game_dtl = msg_txt.split('\n')[1]
        movies_guessed = 0
        trophy_symbol = u'\U0001f3c6'
        check_mark = u'\u2705'

        # check for overall score and movies_guessed
        for line in msg_txt.split('\n'):

            if line.find(trophy_symbol) >= 0:
                game_score = line.split(' ')[1]

            if line.find(check_mark) >= 0:
                movies_guessed += 1

        logger.debug(f"{movies_guessed} correctly guessed")
        metric_01 = movies_guessed

    if game_prefix == 'atlantic':
        game_name = 'atlantic'
        msg_txt = msg_txt.replace('[', '')

        # find position of colon for time, slash for date
        s = msg_txt.find(':')
        d = msg_txt.find('/')
        if s == -1 or d == -1:
            msg_back = [False, 'Invalid format']
            return msg_back

        # find score and date
        game_score = msg_txt[s - 2:s + 3].strip()
        r_month = msg_txt[d - 2:d].strip().zfill(2)
        r_day = msg_txt[d + 1:d + 3].strip().zfill(2)

        # find year (this is generally not working)
        if '202' in msg_txt:
            y = msg_txt.find('202')
            r_year = msg_txt[y:y + 4]
        else:
            r_year = game_date[0:4]

        game_date = f'{r_year}-{r_month}-{r_day}'

    # put into dataframe
    my_cols = ['game_date', 'game_name', 'game_score', 'added_ts', 'discord_id', 'game_dtl', 'metric_01', 'metric_02', 'metric_03']
    my_data = [[game_date, game_name, game_score, added_ts, discord_id, game_dtl, metric_01, metric_02, metric_03]]
    df = pd.DataFrame(data=my_data, columns=my_cols)

    # append to mySQL
    engine = create_engine(sql_addr)
    df.to_sql(name='game_history', con=engine, if_exists='append', index=False)

    msg_back = f"Added {game_name} for {discord_id} on {game_date} with score {game_score}"

    return msg_back

# check for leader changes
def mini_leader_changed(guild_id):
    engine = create_engine(sql_addr)
    connection = engine.connect()
    query = f"""
        SELECT guild_id, winners_changed
        FROM mini_leader_changed
        WHERE guild_id = :guild_id AND winners_changed = 1
    """

    try:
        result = connection.execute(text(query), {"guild_id": guild_id})
        row = result.fetchone()

        if row:
            return True
        else:
            return False
    finally:
        connection.close()
