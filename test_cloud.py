
## for use on pythonanywhere.com

import os
from sqlalchemy import create_engine
import pandas as pd
import bot_functions as bf

# login
sql_pass = os.getenv('MYSQLPASS')
sql_user = 'matttebbetts'

# connection
sql_host = 'matttebbetts.mysql.pythonanywhere-services.com'
sql_port = '3306'
database = 'matttebbetts$crossword'

# create
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"
engine = create_engine(sql_addr)

# send dataframe as test
df = pd.read_csv('files/users.csv', dtype={'discord_id_nbr': str})
bf.tab_df(df.head())


