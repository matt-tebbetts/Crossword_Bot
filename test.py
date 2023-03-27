import pandas as pd
import numpy as np
from tabulate import tabulate

df = pd.read_csv('files/user_dtl.csv')
#df['is_different'] = np.where(df['old_number'] == df['new_number'], 0, 1)
print(tabulate(df, headers='keys', tablefmt='psql'))
