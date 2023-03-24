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
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import logging
import bot_camera

# Create a formatter that includes a timestamp
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Create a logger and set its log level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# set global variables
local_mode = True if socket.gethostname() == "MJT" else False

# load environment variables
crossword_channel_id = 806881904073900042

# set file locations
img_loc = 'files/images/'

# get secrets
load_dotenv()
sql_pass = os.getenv("SQLPASS")
sql_user = os.getenv("SQLUSER")
sql_host = os.getenv("SQLHOST")
sql_port = os.getenv("SQLPORT")
database = os.getenv("SQLDATA")
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"
cookie = os.getenv('NYT_COOKIE')


# save mini dataframe and send image
def get_mini(is_family=False):

    # get mini date
    now = datetime.now(pytz.timezone('US/Eastern'))
    now_ts = now.strftime("%Y-%m-%d %H:%M:%S")
    cutoff_hour = 17 if now.weekday() in [5, 6] else 21
    if now.hour > cutoff_hour:
        mini_dt = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        mini_dt = now.strftime("%Y-%m-%d")

    # get leaderboard html
    leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
    html = requests.get(leaderboard_url, cookies={'NYT-S': cookie})

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
    df.insert(0, 'game_date', mini_dt)
    df['added_ts'] = now_ts

    # if empty
    if len(df) == 0:
        logger.debug('Nobody did the mini yet')
        return None

    # append to mySQL
    engine = create_engine(sql_addr)
    df.to_sql(name='mini_history', con=engine, if_exists='append', index=False)

    # get user detail from sql
    my_query = """select * from users"""
    users = pd.read_sql(my_query, con=engine)

    # merge with users
    img_df = pd.merge(df, users, how='inner', on='player_id')

    # determine family or friends list
    if is_family:
        img_df = img_df[(img_df['give_rank'] == False) | (img_df['player_name'] == 'Matt')][
            ['player_name', 'game_time']].reset_index(drop=True)
    else:
        img_df = img_df[img_df['give_rank'] == True][
            ['player_name', 'game_time']].reset_index(drop=True)

    # create rank
    game_rank = img_df['game_time'].rank(method='dense').astype(int)
    img_df.insert(0, 'game_rank', game_rank)

    # find winner(s) and create tagline for subtitle
    winners = img_df.loc[img_df['game_rank'] == 1]['player_name'].unique()

    # get custom taglines
    if now.hour < cutoff_hour:
        tagline = "It ain't over til it's over"
    elif len(winners) > 1:
        tagline = "It's a tie!"
    else:
        winner = winners[0]
        if winner == 'Brice':
            tagline = "Mooooooooo"
        elif winner == 'Zach':
            tagline = "We've been Throoped!"
        elif winner == 'Matt':
            tagline = "It's me. Hi."
        elif winner == 'Aaron':
            tagline = "Well look who decided to play today."
        else:
            tagline = f"A wild {winner} appeared!"

    # image creation
    img_df.rename(columns={'game_rank':'rank', 'player_name':'player', 'game_time':'time'}, inplace=True) # forgot POINTS
    img_title = f"Mini: {mini_dt}"
    img = bot_camera.dataframe_to_image_dark_mode(img_df, img_title=img_title)
    logger.debug('Got the mini.')

    return img


# add discord scores to database when people paste them to discord chat
def add_score(game_prefix, discord_id, msg_txt):
    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    game_date = now.strftime("%Y-%m-%d")
    game_time = now.strftime("%Y-%m-%d %H:%M:%S")

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
    my_data = [[game_date, game_name, game_score, game_time, discord_id, game_dtl, metric_01, metric_02, metric_03]]
    df = pd.DataFrame(data=my_data, columns=my_cols)

    # append to mySQL
    engine = create_engine(sql_addr)
    df.to_sql(name='game_history', con=engine, if_exists='append', index=False)

    msg_back = [True, f'Added {game_name} score for {discord_id}']

    return msg_back
