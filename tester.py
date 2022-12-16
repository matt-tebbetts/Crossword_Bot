import numpy as np
import pandas as pd
import pandasql as ps
from tabulate import tabulate
from datetime import datetime

# nice printer
def print_nicely(df_to_print):
    return print(tabulate(df_to_print, headers='keys', tablefmt='psql'))


# get Mini history
mini_history = 'files/mini_history.csv'
df_raw = pd.read_csv(mini_history)

# only keep first record for each day+player
df_raw['added_rank'] = df_raw.groupby(['game_date', 'player_id'])['added_ts'].rank()
df_raw = df_raw[1 == df_raw['added_rank']][['game_date', 'player_id', 'game_time', 'added_ts']]

# get real names
mini_names = 'files/mini_names.csv'
df_names = pd.read_csv(mini_names)
df_names = df_names[df_names['give_rank'] == True]

# combine
df = pd.merge(
    df_raw, df_names, how='inner', on='player_id'
)[['game_date', 'game_time', 'player_name']].sort_values(by=['game_date', 'game_time']).reset_index(drop=True)

# add rank, points, and week
y = 11
df['game_rank'] = df.groupby(['game_date'])['game_time'].rank(method='dense').astype(int)
df['points'] = np.where(df['game_rank'] < y, pow(y - df['game_rank'], 2), 0)
df['game_yr_wk'] = df['game_date'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%Y-%U'))

# get this week's dataframe
this_week = df[df['game_yr_wk'] == df['game_yr_wk'].max()]

# get list of each person's ranks
this_week_ranks = this_week.groupby('player_name')['game_rank'].apply(list).reset_index(name='ranks')

# get weekly leaderboard
query_this_week = """
    with temp as (
    select *
    from df
    where game_yr_wk = (select max(game_yr_wk) from df)
    )
    
    select  
        *, 
        rank() over(order by points desc) as week_rank
    from
            (
            select 
                player_name,
                sum(points) as points
            from temp
            group by 
                player_name
            )
"""

# get this week's leaderboard
df_this_week = ps.sqldf(query_this_week).set_index('player_name')

# combine with ranks
df_this_week_with_ranks = pd.merge(df_this_week, this_week_ranks, how='inner', on='player_name')

print('leaderboard: this week')
print_nicely(df_this_week_with_ranks)

img_filepath = 'files/games/Mini/this_week.png'

# run function to generate chart image
fig = img.render_mpl_table(df_this_week_with_ranks, chart_title='Weekly Leaderboard').figure
fig.savefig(img_filepath, dpi=300, bbox_inches='tight', pad_inches=.5)
print(fig)
print('successfully saved image of chart')