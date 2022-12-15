
# Import the required libraries

import os
path_to_json = 'bq_key.json'
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path_to_json

import pandas as pd

# Set the project, dataset, and table names
project = 'angular-operand-300822'
dataset = 'crossword'
table = 'mini_view'

query = "select * from " + dataset + "." + table

df = pd.read_gbq(query, project_id=project)

# Print the dataframe
print(df.head())