import pandas as pd
import bot_functions as b
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# save loc
my_fil = 'files/images/test.png'

# read test csv to dataframe
df = pd.read_csv('files/mini_history.csv')
df = df[df['game_date']=='2023-03-15']
df = df[df['added_ts']=='2023-03-14 22:29:10']

# render table as figure and save
fig = b.render_mpl_table(df, chart_title='test').figure
fig.savefig(my_fil, dpi=300, bbox_inches='tight', pad_inches=0.25)

image = mpimg.imread(my_fil)
plt.imshow(image)
plt.show()