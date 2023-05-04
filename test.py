import requests
import re
from bs4 import BeautifulSoup
import json
import pandas as pd

tickers = ['SHOP', 'AMZN'] #, 'NVDA', 'AMD', 'ROL', 'BXC', 'TREX', 'GOOGL', 'AI', 'PLTR', 'SNOW', 'TSLA', 'AAPL', 'MSFT', 'META', 'NFLX', 'SQ', 'PYPL', 'ZM', 'UBER', 'LYFT']
dataframes = []

for ticker in tickers:
    # Make a GET request to the URL
    url = f"https://www.macrotrends.net/stocks/charts/{ticker}/company/financial-statements"
    response = requests.get(url)

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the script tag containing the originalData variable using a regular expression pattern
    pattern = re.compile(r'var originalData = (\[.*?\]);')
    script_tag = soup.find('script', text=pattern)

    # Extract the data from the originalData variable
    if script_tag:
        json_text = pattern.search(script_tag.string).group(1)
        data = json.loads(json_text)

        data_df = pd.DataFrame(data)
        data_df.drop(columns="popup_icon", inplace=True)

        # Melt the dataframe to transform the date columns into rows
        data_melted = pd.melt(data_df, id_vars='field_name', var_name='date', value_name='value')

        # Extract just the year from the date column
        data_melted['year'] = data_melted['date'].apply(lambda x: x.split('-')[0])

        # Extract the text between the HTML tags in the field_name column
        data_melted['field_name'] = data_melted['field_name'].apply(lambda x: re.search(r'>(.*?)<', x).group(1))

        # Drop the date column
        data_melted = data_melted.drop('date', axis=1)

        # Rename the columns
        data_melted.columns = ['field_name', 'value', 'year']

        # add ticker and financial statement type
        data_melted['ticker'] = ticker
        data_melted['statement_type'] = 'Cash Flow'

        # Reorder the columns
        data_melted = data_melted[['ticker', 'statement_type', 'field_name', 'year', 'value']]

        # Multiply values by one million if "per share" is not in field_name
        data_melted.loc[~data_melted['field_name'].str.contains('per share'), 'value'] *= 1000000

        # add to dataframes list
        dataframes.append(data_melted)

        print(f'got data for {ticker}')

    else:
        print(f'Could not find originalData variable for {ticker} in HTML content.')

# Combine all dataframes into one
df = pd.concat(dataframes)

# Export the combined dataframe to CSV
df.to_csv('files/test.csv', index=False)

# Print the dataframe
print(df)
