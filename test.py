from tabulate import tabulate
import pandas as pd

df = pd.read_csv('files/archive/users.csv')

print(tabulate(df, headers='keys', tablefmt='psql'))
