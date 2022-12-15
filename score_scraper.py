
# for getting date and time
import pytz
from datetime import datetime
import pandas as pd
from os.path import exists
from tabulate import tabulate

# get date and time
now = datetime.now(pytz.timezone('US/Eastern'))
game_date = now.strftime("%Y-%m-%d")
game_time = now.strftime("%Y-%m-%d %H:%M:%S")

# add scores to database
def add_score(game_id, user_id, msg_txt):
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
    my_cols = ['game_date', 'game_name', 'game_score', 'added_ts', 'user_id', 'game_dtl']
    my_data = [[game_date, game_name, game_score, game_time, user_id, game_dtl]]
    df = pd.DataFrame(data=my_data, columns=my_cols)
    print('I created this dataframe:')
    print(tabulate(df, headers='keys', tablefmt='psql'))
    print('')

    # send to csv
    send_to_csv = True
    if send_to_csv:
        save_loc = 'files/games/game_history.csv
        df.to_csv(save_loc, mode='a', index=False, header=False)
        print('I saved this score to : ' + save_loc)

    # confirmation message
    msg_back = f"Hi {user_id}, I saved your {game_name} score of {game_score} for {game_date}"""

    return msg_back
