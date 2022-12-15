from tabulate import tabulate
import pandas as pd
import numpy as np
from sys import exit

# pull game_history
df = pd.read_csv('files/game_history.csv')

# remove dupes
df['game_dtl'] = df['game_dtl'].mask(pd.isnull, 'None')
df['x'] = df.groupby(['game_date', 'game_name', 'game_dtl', 'user_id'])['added_ts'].rank(method='first')
df = df[df['x'] == 1]

print(tabulate(df, headers='keys', tablefmt='psql'))

df = df[df['game_name'] != 'BoxOffice']

print('adding points now')
max_g = df['game_score'].str[2].astype(int)
act_g = df['game_score'].str[0].replace('X', 0).astype(int)
df['played'] = 1
df['won'] = np.minimum(act_g, 1)
df['guesses'] = np.where(act_g == 0, np.NaN, act_g)
df['points'] = np.where(act_g == 0, 0, pow((max_g + 1) - act_g, 2))

print(tabulate(df, headers='keys', tablefmt='psql'))

# group
g = df.groupby(['game_name', 'user_id'], as_index=False) \
    .agg({'played': 'sum', 'won': 'sum', 'points': 'sum', 'guesses': 'mean'}) \
    .sort_values(by='points', ascending=False) \
    .rename(columns={'guesses': 'avg_guess'})
print(g)
