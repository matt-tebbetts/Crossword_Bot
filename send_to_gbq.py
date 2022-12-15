

from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

# set google credentials
path_to_json = 'bq_key.json'
my_credentials = service_account.Credentials.from_service_account_file(path_to_json)

# connect to client
my_project = 'angular-operand-300822'
client = bigquery.Client(credentials=my_credentials, project=my_project)
print('nice: connected!')

# get csv
my_csv = 'files/2022-12-09.csv'
df = pd.read_csv(my_csv)

# send to bq
send_it = True
if send_it:
    my_table = 'crossword.mini_history'
    df.to_gbq(
            destination_table=my_table,
            project_id=my_project,
            #credentials=my_credentials,
            if_exists='append')