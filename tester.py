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

# get cookie
load_dotenv()
COOKIE = os.getenv('NYT_COOKIE')

# get leaderboard html
leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
html = requests.get(leaderboard_url, cookies={'NYT-S': COOKIE})
print('going to NYT website...')

no_mini_yet = []

# find scores in the html
soup = BeautifulSoup(html.text, features='lxml')
divs = soup.find_all("div", class_='lbd-score')
scores = {}
for div in divs:
    name = div.find("p", class_='lbd-score__name').getText().strip().replace(' (you)', '')
    time_div = div.find("p", class_='lbd-score__time')
    if time_div:
        time = time_div.getText()
        if time == '--':
            no_mini_yet.append(name)
        else:
            scores[name] = time

print(no_mini_yet)