import os
import requests
import pandas as pd
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import numpy as np
import matplotlib.pyplot as plt
import six
import pytz
from datetime import datetime
from tabulate import tabulate

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
COOKIE = os.getenv('NYT_COOKIE')


## generic functions

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


## project-specific functions

# get current mini
def get_nyt(mini_dt, now_ts):
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

    return df


# add discord scores to database
def add_score(game_id, player_id, msg_txt):
    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    game_date = now.strftime("%Y-%m-%d")
    game_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # set these up
    game_name = None
    game_score = None
    game_dtl = None

    if game_id == "#Worldle":
        game_name = "Worldle"
        game_score = msg_txt[14:17]

    if game_id == "Wordle":
        game_name = "Wordle"
        game_score = msg_txt[11:14]

    if game_id == "Factle.app":
        game_name = "Factle"
        game_score = msg_txt[14:17]
        game_dtl = msg_txt.splitlines()[1]

    if game_id == 'boxofficega.me':
        game_name = 'BoxOffice'
        game_dtl = msg_txt.split('\n')[1]
        trophy_symbol = u'\U0001f3c6'
        for line in msg_txt.split('\n'):
            if line.find(trophy_symbol) >= 0:
                game_score = line.split(' ')[1]

    # put into dataframe
    my_cols = ['game_date', 'game_name', 'game_score', 'added_ts', 'player_id', 'game_dtl']
    my_data = [[game_date, game_name, game_score, game_time, player_id, game_dtl]]
    df = pd.DataFrame(data=my_data, columns=my_cols)
    print('I created this dataframe:')
    print(tabulate(df, headers='keys', tablefmt='psql'))
    print('')

    # send to csv
    send_to_csv = True
    if send_to_csv:
        save_loc = 'files/games/mini_history.csv'
        df.to_csv(save_loc, mode='a', index=False, header=False)
        print('I saved this score to : ' + save_loc)

    # confirmation message
    msg_back = f"Hi {player_id}, I saved your {game_name} score of {game_score}"""

    return msg_back


# create leaderboard images
def get_leaderboard(game_id):

    if str.lower(game_id) not in ['wordle', 'worldle', 'factle']:
        print('sorry, not set up yet')
        return

    # (should just build match dataframe or dictionary)
    # set proper case of game name (need to adjust for boxoffice)
    game_id = str.upper(game_id[0]) + str.lower(game_id[1:len(game_id)])

    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    now_date = now.strftime("%Y-%m-%d")

    # pull game_history
    raw_df = pd.read_csv('files/game_history.csv')
    raw_df = raw_df[raw_df['game_name'] == game_id]
    user_df = pd.read_csv('files/users.csv')[['player_id', 'player_name']]
    df = pd.merge(raw_df, user_df, how='left', on='player_id')[
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

    # rename
    df.rename(columns={'game_score': 'score', 'player_name': 'player'}, inplace=True)

    guessing_games = ['Wordle', 'Worldle', 'Factle']
    if game_id in guessing_games:
        # build daily leaderboard
        df_day = df[(df['game_name'] == game_id) & (df['game_date'] == now_date)][['player', 'score', 'points']]
        rank = df_day['points'].rank(method='dense', ascending=False)
        df_day.insert(loc=0, column='rank', value=rank)
        df_day.set_index('rank', drop=True, inplace=True)
        df_day.sort_values(by='points', ascending=False, inplace=True)
        print('daily for ' + game_id)

        # save image
        path_daily = 'files/daily/' + game_id + '.png'
        chart_title = f'{game_id}, {now_date}'
        fig = render_mpl_table(df_day, chart_title=chart_title).figure
        fig.savefig(path_daily, dpi=300, bbox_inches='tight', pad_inches=.5)
        print(f'ok, printed daily leaderboard image for {game_id} to {path_daily}')
        print('')

        # create weekly leaderboard
        current_week = np.max(df['week_nbr'])
        df_week = df[(df['game_name'] == game_id) & (df['week_nbr'] == current_week)]
        df_week = df_week \
            .groupby(['week_nbr', 'game_name', 'player'], as_index=False) \
            .agg({'played': 'sum',
                  'won': 'sum',
                  'points': 'sum',
                  'guesses': 'mean'}) \
            .sort_values(by='points', ascending=False) \
            .rename(columns={'guesses': 'avg_guess'})
        rank = df_week.groupby(['game_name'])['points'].rank(method='dense', ascending=False).astype(int)
        df_week.insert(loc=0, column='rank', value=rank)
        df_week.drop(columns={'week_nbr', 'game_name'}, inplace=True)
        df_week.set_index('rank', drop=True, inplace=True)
        df_week['avg_guess'] = np.round(df_week['avg_guess'], 1)
        print('weekly for ' + game_id)
        print(tabulate(df_week, headers='keys', tablefmt='psql'))
        print('')

        # save image
        path_wkly = 'files/weekly/' + game_id + '.png'
        fig = render_mpl_table(df_week, chart_title=f'{game_id}, Week #{current_week}').figure
        fig.savefig(path_wkly, dpi=300, bbox_inches='tight', pad_inches=.5)
        print(f'ok, printed weekly leaderboard image for {game_id} to {path_wkly}')
        print('')
