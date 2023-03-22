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

# create image of dataframe
def render_mpl_table(data, col_width=3.5, row_height=0.625, font_size=16,
                     header_color='#2c2f33', row_colors=['#3c3f41', '#3c3f41'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0, chart_title='Title',
                     ax=None, fig_bg_color='#23272a', **kwargs):
    if ax is None:
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)

        # set facecolors
        ax.set_facecolor(fig_bg_color)
        fig.set_facecolor(fig_bg_color)
        
        ax.axis('off')

        ax.set_title(label=chart_title,
                     fontdict=dict(fontsize=18, verticalalignment='baseline', horizontalalignment='center', color='w')
                     )
    
    # set the data
    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

    # set font size?
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    # format the cells
    for k, cell in six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_text_props(color='w')
            cell.set_facecolor(row_colors[k[0] % len(row_colors)])

    return ax


# get dataframe
df = pd.read_csv('files/mini_dark.csv')

# create image of dataframe
img_file = f'files/images/mini_dark.png'
img_title = f"The Mini dark mode test"
fig = render_mpl_table(df, chart_title=img_title, fig_bg_color='#23272a').figure
fig.savefig(img_file, dpi=300, bbox_inches='tight', pad_inches=.5, facecolor=fig.get_facecolor())

