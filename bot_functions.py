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
from tabulate import tabulate
from sqlalchemy import create_engine

# set global variables
local_mode = True if socket.gethostname() == "MJT" else False

# load environment variables
load_dotenv()
crossword_channel_id = 806881904073900042

# set file locations
if local_mode:
    img_loc = 'files/images/'
    user_csv = 'files/users.csv'
    mini_csv = 'files/mini_history.csv'
    game_csv = 'files/game_history.csv'
else:
    img_loc = '/home/matttebbetts/projects/Crossword_Bot/files/images/'
    user_csv = '/home/matttebbetts/projects/Crossword_Bot/files/users.csv'
    mini_csv = '/home/matttebbetts/projects/Crossword_Bot/files/mini_history.csv'
    game_csv = '/home/matttebbetts/projects/Crossword_Bot/files/game_history.csv'

# set mySQL details
sql_pass = os.getenv("SQLPASS")
sql_user = os.getenv("SQLUSER")
sql_host = os.getenv("SQLHOST")
sql_port = os.getenv("SQLPORT")
database = os.getenv("SQLDATA")
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"


# print a dataframe nicely
def tab_df(data):
    return print(tabulate(data, headers='keys', tablefmt='psql'))


# create image of dataframe
def render_mpl_table(data, col_width=2.5, row_height=0.625, font_size=16,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0, chart_title='Title',
                     ax=None, **kwargs):
    if ax is None:
        # set size of image?
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)

        # set axis on or off?
        ax.axis('off')

        # set title
        ax.set_title(label=chart_title,
                     fontdict=dict(fontsize=18, verticalalignment='baseline', horizontalalignment='center')
                     )

    # this makes the dataframe into the "table" image
    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

    # table details (font size?)
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    # format the lines and edges?
    for k, cell in six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0] % len(row_colors)])

    # end of function is to return the "ax" variable? why not .figure?
    return ax


# save mini dataframe and send image
def get_mini(is_family=False):
    load_dotenv()
    cookie = os.getenv('NYT_COOKIE')

    # get mini date
    now = datetime.now(pytz.timezone('US/Eastern'))
    now_ts = now.strftime("%Y-%m-%d %H:%M:%S")
    cutoff_hour = 17 if now.weekday() in [5, 6] else 21

    # if we're past cutoff_hour, mini is on tomorrow's date
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

    # check if anyone did it yet
    if len(df) == 0:
        print('Nobody did the mini yet')
        no_mini = f'{img_loc}No_Mini_Yet.png'
        return no_mini

    # append to csv history
    df.to_csv(mini_csv, mode='a', index=False, header=False)

    # append to mySQL
    send_to_sql = True
    if send_to_sql:

        # this should now be sent to the custom function we create called like "get_engine" which could return the engine
        engine = create_engine(sql_addr)
        df.to_sql(name='mini_history', con=engine, if_exists='append', index=False)

    ## everything below should be within its own separate function

    # get user detail
    users = pd.read_csv(user_csv)
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

    # if we're past the nightly cutoff time, or before the cutoff hour:
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
            tagline = "Yeah baby, yeah!"
        elif winner == 'Aaron':
            tagline = "Well look who decided to play today!"
        elif winner == 'Samantha':
            tagline = "Slammin' Sammy!"
        else:
            tagline = f"A wild {winner} appeared!"

    # create image
    img_file = f'{img_loc}daily_mini.png'
    img_title = f"The Mini \n {mini_dt} \n \n {tagline} \n"
    fig = render_mpl_table(img_df, chart_title=img_title).figure
    fig.savefig(img_file, dpi=300, bbox_inches='tight', pad_inches=.5)
    print('mini: got the mini')

    # send image back to discord
    return img_file
    # return [True, img_file, no_mini_list]


# add discord scores to database
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
        print(f"got {metric_03} green frogs")

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

        print(f"{movies_guessed} correctly guessed")
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

    # send to csv
    df.to_csv(game_csv, mode='a', index=False, header=False)

    # append to mySQL
    send_to_sql = True
    if send_to_sql:
        engine = create_engine(sql_addr)
        df.to_sql(name='game_history', con=engine, if_exists='append', index=False)

    msg_back = [True, 'sent to CSV and SQL']

    return msg_back


# this creates and sends an image of the requested leaderboard
def get_leaderboard(game_name, time_frame):
    print(f'fetching {time_frame} for {game_name}')

    # presets
    cond1 = False
    cond2 = False

    # get mini date to know which day is "today" for mini
    if game_name == 'mini':
        # get mini date
        now = datetime.now(pytz.timezone('US/Eastern'))
        cond1 = (now.weekday() >= 5 and now.hour >= 18)  # weekend night (after 6pm)
        cond2 = (now.weekday() <= 4 and now.hour >= 22)  # weekday night (after 10pm)
        if cond1 or cond2:
            mini_dt = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            mini_dt = now.strftime("%Y-%m-%d")

    # determine the requested timeframe details
    if time_frame in ['this week', 'current week', 'weekly']:
        time_category = 'weekly'
        time_field = 'is_this_week'
    elif time_frame in ['last week', 'previous week']:
        time_category = 'weekly'
        time_field = 'is_last_week'
    elif time_frame in ['daily', 'today', 'current', 'current day']:
        time_category = 'daily'
        if game_name == 'mini' and (cond1 or cond2):
            time_field = 'current_date("America/New_York")+1'
        else:
            time_field = 'current_date("America/New_York")'
    elif time_frame in ['yesterday', 'previous']:
        time_category = 'daily'
        if game_name == 'mini' and (cond1 or cond2):
            time_field = 'current_date("America/New_York")'
        else:
            time_field = 'current_date("America/New_York")-1'
    else:
        response = [False, f'Invalid entry {time_frame}', None]
        return response

    if time_category == 'daily':
        my_query = """
            select *
            from `crossword.all_games`
            where game_name = '""" + game_name + """'
            and game_date = """ + time_field + """
        """
        df = pd.read_gbq(my_query, project_id=my_project)[
            ['game_date', 'game_rank', 'player_name', 'game_score', 'points']]

        # get time detail and set columns for nice image
        time_category_dtl = df['game_date'].unique()[0]
        img_df = df.loc[:, df.columns != 'game_date'].sort_values(by='game_rank')

    if time_category == 'weekly':
        my_query = """
            select *
            from `crossword.leaders_weekly`
            where game_name = '""" + game_name + """'
            and """ + time_field + """
        """

        # read CSV instead of BQ
        #df = pd.read_csv(game_csv)

        df = pd.read_gbq(my_query, project_id=my_project)[
            ['game_week', 'week_rank', 'player_name', 'games', 'wins', 'points']]

        # get time detail and set columns for nice image
        time_category_dtl = df['game_week'].unique()[0]
        img_df = df.loc[:, df.columns != 'game_week']

    # create image
    chart_title = f'{game_name}_{time_category}_{time_category_dtl}'
    img_save_as = f'{img_loc}{game_name}_{time_category}_{time_category_dtl}.png'
    fig = render_mpl_table(img_df, chart_title=chart_title).figure
    fig.savefig(img_save_as, dpi=300, bbox_inches='tight', pad_inches=.5)
    print(f'printed {time_frame} leaderboard image for {game_name} to {img_save_as}')

    # response is [True/False, Comment, Image Location]
    response = [True, f'Got {time_category} {game_name} leaderboard for {time_category_dtl}', img_save_as]
    return response
