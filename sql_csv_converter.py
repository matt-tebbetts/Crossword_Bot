import pandas as pd
import bot_functions as bf
from sqlalchemy import create_engine
import numpy as np

# set sql db details
sql_user = 'root'
sql_pass = '$3Trill10N2' # REPLACE THIS
sql_host = 'localhost' # ? 127.0.0.1 worked...
sql_port = '3306'
sql_dbnm = 'games'

# create a connection to the MySQL server
engine = create_engine(f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{sql_dbnm}")

my_tbl = 'mini_history'
my_fil = f'files/{my_tbl}.csv'

## ************ select only ONE ***************** ##
sql_to_csv = False
csv_to_sql = True
## ************ select only ONE ***************** ##

if sql_to_csv == csv_to_sql:
    print("pick one or the other")
    exit()

# send SQL to CSV
if sql_to_csv:
    query = f"select * from {my_tbl}"
    df = pd.read_sql(query, engine).fillna(np.nan)
    df.to_csv(my_fil, index=False)

# send CSV to SQL
if csv_to_sql:
    df = pd.read_csv(my_fil)
    df.to_sql(name=my_tbl, con=engine, if_exists='replace', index=False)
