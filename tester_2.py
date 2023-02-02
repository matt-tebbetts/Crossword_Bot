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
import bot_functions as bf
import os

import inspect

# send message and tag users
warning_msg = inspect.cleandoc(f"""The mini expires at now!
                The following players have not done the mini today: 
                """)
user_id = 'matt'
warning_msg += f"<@{user_id}> "
warning_msg += "\n"
warning_msg += "To remove this notification, type '/mini_warning remove' (without the quotes)"

print(f"warning: {warning_msg}")