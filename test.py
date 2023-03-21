import os
import re
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load MySQL details from environment variables
load_dotenv()
sql_pass = os.getenv("SQLPASS")
sql_user = os.getenv("SQLUSER")
sql_host = os.getenv("SQLHOST")
sql_port = os.getenv("SQLPORT")
database = os.getenv("SQLDATA")
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"
engine = create_engine(sql_addr)

url = "http://nyt.aromatt.net/times/"
response = requests.get(url)
html_content = response.text

csv_files = re.findall(r"(\d{4}-\d{2}-\d{2}\.csv)", html_content)

dfs = []

for csv_file in csv_files:
    game_date = datetime.strptime(csv_file[:-4], "%Y-%m-%d")
    if (datetime.now() - game_date).days <= 90:
        csv_url = url + csv_file
        csv_content = requests.get(csv_url).text
        df = pd.read_csv(StringIO(csv_content))
        df.insert(0, "game_date", game_date)
        dfs.append(df)

combined_df = pd.concat(dfs)
combined_df.columns = ['game_date', 'player_id', 'game_time']

# Add timestamp
combined_df['py_insert_ts'] = datetime.now()

# Send the combined DataFrame to the MySQL database
combined_df.to_sql('mini_backups', engine, if_exists='append', index=False)
