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

# set global variables
test_mode = True if socket.gethostname() == "MJT" else False
print(test_mode)

my_project = 'angular-operand-300822'
mini_history = 'crossword.mini_history'
game_history = 'crossword.game_history'

## ------------------------------------------------------------------------------------------- ##

# print a dataframe nicely
def tab_df(data):
    return print(tabulate(data, headers='keys', tablefmt='psql'))


# create image of dataframe
def render_mpl_table(data, col_width=2.5, row_height=0.625, font_size=14,
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


## ------------------------------------------------------------------------------------------- ##

# save mini dataframe and send image
def get_mini():
    # get cookie
    load_dotenv()
    COOKIE = os.getenv('NYT_COOKIE')

    print('current directory is: ' + os.getcwd())

    # get mini date
    now = datetime.now(pytz.timezone('US/Eastern'))
    now_ts = now.strftime("%Y-%m-%d %H:%M:%S")
    cond1 = (now.weekday() >= 5 and now.hour >= 18)
    cond2 = (now.weekday() <= 4 and now.hour >= 22)
    if cond1 or cond2:
        mini_dt = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        mini_dt = now.strftime("%Y-%m-%d")

    # get leaderboard html
    leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
    html = requests.get(leaderboard_url, cookies={'NYT-S': COOKIE})

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
    df.insert(0, 'game_date', mini_dt)
    df['added_ts'] = now_ts

    # check if anyone did it yet
    if len(df) == 0:
        print('Nobody did the mini yet')
        no_mini = '/home/matttebbetts/projects/Crossword_Bot/files/images/No_Mini_Yet.png'
        return no_mini

    # set location for csv file
    if test_mode:
        mini_history_loc = 'files/mini_history.csv'
    else:
        mini_history_loc = '/home/matttebbetts/projects/Crossword_Bot/files/mini_history.csv'

    # append to master file
    df.to_csv(mini_history_loc, mode='a', index=False, header=False)
    print('mini: saved to master file')
    print('mini: attempting to send to BigQuery')

    # append to bq
    try:
        df.to_gbq(destination_table=mini_history, project_id=my_project, if_exists='append')
        print('mini: successfully sent to BQ')
    except Exception as e:
        print('mini: ERROR. did not send to BQ')

    # set up for image creation
    real_names = pd.read_csv('/home/matttebbetts/projects/Crossword_Bot/files/users.csv')
    img_df = pd.merge(df, real_names, how='inner', on='player_id')
    img_df = img_df[img_df['give_rank'] == True][['player_name', 'game_time']].reset_index(drop=True)
    game_rank = img_df['game_time'].rank(method='dense').astype(int)
    img_df.insert(0, 'game_rank', game_rank)

    # create image
    img_file = '/home/matttebbetts/projects/Crossword_Bot/files/daily/Mini.png'
    img_title = f"The Mini: {mini_dt}"
    fig = render_mpl_table(img_df, chart_title=img_title).figure
    fig.savefig(img_file, dpi=300, bbox_inches='tight', pad_inches=.5)
    print('mini: image output created')

    # send image back to discord
    return img_file

# add discord scores to database
def add_score(game_prefix, player_id, msg_txt):
    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    game_date = now.strftime("%Y-%m-%d")
    game_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # set these up
    game_name = None
    game_score = None
    game_dtl = None

    if game_prefix == "#Worldle":
        game_name = "worldle"
        game_score = msg_txt[14:17]

    if game_prefix == "Wordle":
        game_name = "wordle"
        game_score = msg_txt[11:14]

    if game_prefix == "Factle.app":
        game_name = "factle"
        game_score = msg_txt[14:17]
        game_dtl = msg_txt.splitlines()[1]

    if game_prefix == 'boxofficega.me':
        game_name = 'boxoffice'
        game_dtl = msg_txt.split('\n')[1]
        trophy_symbol = u'\U0001f3c6'
        for line in msg_txt.split('\n'):
            if line.find(trophy_symbol) >= 0:
                game_score = line.split(' ')[1]

    if game_prefix == 'atlantic':
        game_name = 'atlantic'
        msg_txt = msg_txt.replace('[', '')

        # find position of colon to get time
        s = msg_txt.find(':')
        game_score = msg_txt[s - 2:s + 3].strip()

        # find position of / to get date
        d = msg_txt.find('/')
        r_month = msg_txt[d - 2:d].strip()
        r_day = msg_txt[d + 1:d + 3].strip()

        # find year (this is generally not working)
        if '202' in msg_txt:
            y = msg_txt.find('202')
            r_year = msg_txt[y:y + 4]
        else:
            r_year = game_date[0:4]

        game_date = f'{r_year}-{r_month}-{r_day}'

    # put into dataframe
    my_cols = ['game_date', 'game_name', 'game_score', 'added_ts', 'player_id', 'game_dtl']
    my_data = [[game_date, game_name, game_score, game_time, player_id, game_dtl]]
    df = pd.DataFrame(data=my_data, columns=my_cols)
    print('I created this dataframe:')
    print(tabulate(df, headers='keys', tablefmt='psql'))
    print('')

    # send to bq
    game_history = 'crossword.game_history'
    my_project = 'angular-operand-300822'
    try:
        df.to_gbq(destination_table=game_history, project_id=my_project, if_exists='append')
        msg_back = 'Got it'
    except:
        msg_back = 'Error: Did not save to BigQuery table'

    return msg_back

# this creates two images (daily + weekly) of the leaderboard into the folder
def get_leaderboard(game_name, time_frame='daily'):
    print(f'fetching {time_frame} for {game_name}')

    if game_name not in ['wordle', 'worldle', 'factle']:
        print('sorry, game_id not set up yet')
        return

    if time_frame not in ['daily', 'weekly']:
        print('sorry, timeframe not set up yet')
        return

    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    now_date = now.strftime("%Y-%m-%d")

    # pull game_history for game_id
    data_df = pd.read_csv('/home/matttebbetts/projects/Crossword_Bot/files/game_history.csv')
    data_df = data_df[data_df['game_name'] == game_name]

    # get player names
    user_df = pd.read_csv('/home/matttebbetts/projects/Crossword_Bot/files/users.csv')[['player_id', 'player_name']]
    data_df['player_id'] = data_df['player_id'].str.lower()
    user_df['player_id'] = user_df['player_id'].str.lower()
    df = pd.merge(data_df, user_df, how='left', on='player_id')[
        ['game_date', 'game_name', 'game_score', 'added_ts', 'game_dtl', 'player_name']]

    # remove dupes and make some adjustments
    df['game_dtl'] = df['game_dtl'].str[0:19].mask(pd.isnull, 'None')
    df['x'] = df.groupby(['game_date', 'game_name', 'game_dtl', 'player_name'])['added_ts'].rank(method='first')
    df = df[df['x'] == 1]
    df['week_nbr'] = pd.to_datetime(df['game_date']).dt.strftime('%Y-%U')

    # calculate points
    max_g = df['game_score'].str[2].astype(int)
    act_g = df['game_score'].str[0].replace('X', 0).astype(int)
    df['played'] = 1
    df['won'] = np.minimum(act_g, 1)
    df['guesses'] = np.where(act_g == 0, max_g + 1, act_g)
    df['points'] = np.where(act_g == 0, 0, pow((max_g + 1) - act_g, 2))

    # do some calcs
    current_week = np.max(df['week_nbr'])

    # if no one has gone yet today, then exit
    if np.max(df['game_date']) != now_date:
        exit_msg = [False, f'No one has completed the {game_name} yet today']
        return exit_msg

    if time_frame == 'daily':
        leaderboard = df[df['game_date'] == now_date][['player_name', 'game_score', 'points']]
        chart_title = f'{time_frame} {game_name}, {now_date}'

    if time_frame == 'weekly':
        leaderboard = df[df['week_nbr'] == current_week][['player_name', 'guesses', 'points']]
        leaderboard['games'] = 1
        leaderboard = leaderboard.groupby(['player_name'], as_index=False) \
            .agg({'games': 'sum',
                  'points': 'sum',
                  'guesses': 'mean'}) \
            .sort_values(by='points', ascending=False) \
            .rename(columns={'guesses': 'avg_guess'})
        leaderboard['avg_guess'] = np.round(leaderboard['avg_guess'], 1)
        chart_title = f'{time_frame} {game_name}, {current_week}'

    # get rank (regardless of timeframe)
    rank = leaderboard['points'].rank(method='dense', ascending=False).astype(int)
    leaderboard.insert(loc=0, column='rank', value=rank)
    leaderboard.set_index('rank', drop=True, inplace=True)
    leaderboard.sort_values(by='points', ascending=False, inplace=True)

    # save image
    img_save_as = f'/home/matttebbetts/projects/Crossword_Bot/files/images/{time_frame}_{game_name}.png'
    fig = render_mpl_table(leaderboard, chart_title=chart_title).figure
    fig.savefig(img_save_as, dpi=300, bbox_inches='tight', pad_inches=.5)
    print(f'printed {time_frame} leaderboard image for {game_name} to {img_save_as}')
    exit_msg = [True, f'Got {game_name} {time_frame}']
    return exit_msg
