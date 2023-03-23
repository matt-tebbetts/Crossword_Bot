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
import logging
import inspect

# set mySQL details
load_dotenv()
sql_pass = os.getenv("SQLPASS")
sql_user = os.getenv("SQLUSER")
sql_host = os.getenv("SQLHOST")
sql_port = os.getenv("SQLPORT")
database = os.getenv("SQLDATA")
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"

# get missing mini report from sql
engine = create_engine(sql_addr)
my_query = """select discord_id_nbr from mini_not_completed"""
players_missing_mini_score = pd.read_sql(my_query, con=engine)['discord_id_nbr'].tolist()

# create warning message
warning_msg = inspect.cleandoc(f"""The mini expires [soon] !
                The following players have not completed today's puzzle:
                """)
for user_id in players_missing_mini_score:
    warning_msg += f"<@{user_id}> "
    warning_msg += "\n"
warning_msg += "To remove this notification, type '/mini_warning remove' (without the quotes)"

print(warning_msg)
