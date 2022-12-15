# set this to true to avoid bigquery during testing
test_mode = False

import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# get mini date
now = datetime.now(pytz.timezone('US/Eastern'))
time_string = now.strftime("%Y-%m-%d %H:%M:%S")
# Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
cond1 = (now.weekday() >= 5 and now.hour >= 18)
cond2 = (now.weekday() <= 4 and now.hour >= 22)
if cond1 or cond2:
    date_string = (now + timedelta(days=1)).strftime("%Y-%m-%d")
else:
    date_string = now.strftime("%Y-%m-%d")

# link to cookie
myfil = 'NYT_COOKIE.txt'
with open(myfil, 'r') as file:
    my_cookie = file.read()
print('successfully read cookie')

# get leaderboard html
leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
html = requests.get(leaderboard_url, cookies={'NYT-S': my_cookie})
print('successfully connected to nytimes.com')

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
print('successfully got mini!')

# put scores into dataframe
df = pd.DataFrame(scores.items(), columns=['player_id', 'game_time'])

# adjustments and timestamp
#df['player_name'] = df['player_name'].str.upper()
df.insert(0, 'game_date', date_string)
df['added_ts'] = time_string
1
# send to csv
csv_dtl = 'mini_history/' + date_string + '.csv'
df.to_csv(csv_dtl, index=False)
print('successfully sent to csv file: ' + csv_dtl)

# save image for bot
import numpy as np
import matplotlib.pyplot as plt
import six

# make simple dataframe for the image
real_names = pd.read_csv(r'/home/matttebbetts/mini_names.csv')
img_df = pd.merge(df, real_names, how='left', on='player_id')
img_df = img_df[img_df['give_rank']==True][['player_name','game_time']].reset_index(drop=True)
img_df['game_rank'] = img_df['game_time'].rank(method='dense').astype(int)

# set-up for image creation
chart_title = 'Mini: ' + date_string
img_filepath = r'/home/matttebbetts/mini_screenshots/latest.png'

# create function to generate image
def render_mpl_table(data, col_width=3.0, row_height=0.625, font_size=14,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0,
                     ax=None, **kwargs):
    if ax is None:

        # set size of image?
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)

        # set axis on or off?
        ax.axis('off')

        # set title
        ax.set_title(label = chart_title,
                     fontdict =
                        {'fontsize': 18,
                         #'fontweight': rcParams['axes.titleweight'],
                         #'color': rcParams['axes.titlecolor'],
                         'verticalalignment': 'baseline',
                         'horizontalalignment': 'center'}
                    )

    # this makes the dataframe into the "table" image
    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

    # table details (font size?)
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    # format the lines and edges?
    for k, cell in  six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0]%len(row_colors) ])

    # end of function is to return the "ax" variable? why not mpl_table?
    return ax

# run function to generate chart image
fig = render_mpl_table(img_df, header_columns=0, col_width=2.0).figure
fig.savefig(img_filepath, dpi=300, bbox_inches='tight', pad_inches=.5)
print('successfully saved image of chart')

# send to master file
history_csv = '/home/matttebbetts/mini_history/mini_history.csv'

# read master file into df
m_df = pd.read_csv(history_csv)

# append today's data
n_df = m_df.append(df)

# send back to file
n_df.to_csv(history_csv, index=False)
print('successfully sent to master csv')

# send to google bigquery
send_to_gbq = True
if send_to_gbq:
    my_project = 'angular-operand-300822'
    my_table = 'crossword.mini_history'
    df.to_gbq(destination_table=my_table, project_id=my_project, if_exists='append') #, progress_bar=False)

print('done: ' + time_string)






