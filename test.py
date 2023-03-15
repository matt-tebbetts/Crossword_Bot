from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
import os
import math

# load env
load_dotenv()

# set mySQL details for NEW database
sql_host = os.getenv("SQLHOST")
sql_user = os.getenv("SQLUSER")
sql_pass = os.getenv("SQLPASS")
sql_port = os.getenv("SQLPORT")
database = os.getenv("SQLDATA")
sql_addr = f"mysql+pymysql://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{database}"

# create engine
engine = create_engine(sql_addr)

# read csv to dataframe
df = pd.read_csv("C:\\Users\\matt_\\Downloads\\users_20230307.csv")

# change formatting of id
df['discord_id_nbr'] = df['discord_id_nbr'].apply(lambda x: '{:.2f}'.format(x))
df['discord_id_nbr'] = df['discord_id_nbr'].str.rstrip('.00')

print(df)

# send to sql
df.to_sql(name='users', con=engine, if_exists='append', index=False)