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
import bot_functions

# file locations
mini_csv = 'files/mini_history.csv'
game_csv = 'files/game_history.csv'


df = pd.read_csv(mini_csv)
