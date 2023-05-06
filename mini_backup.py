import os
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from io import StringIO
from config import credentials, sql_addr
from sqlalchemy import create_engine

# The URL to be scraped
url = "http://nyt.aromatt.net/times/"

# Fetch the HTML content using requests
response = requests.get(url)

# Initialize an empty DataFrame to store the data
combined_df = pd.DataFrame()

if response.status_code == 200:
    # Parse the HTML content using Beautiful Soup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find all 'a' tags with an href attribute containing '.csv'
    csv_links = soup.find_all('a', href=re.compile(r'\.csv'))

    # Iterate through the CSV links
    for link in csv_links:
        # Extract the CSV URL and file name
        csv_url = os.path.join(url, link['href'])
        file_name = link['href']

        # Extract the date from the file name
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
        game_date = date_match.group(1) if date_match else None

        # limit which files to pull
        if game_date < '2023-05-01':
            continue

        # Download the CSV and read it into a DataFrame
        csv_response = requests.get(csv_url)
        csv_content = csv_response.content.decode('utf-8')

        # Create a DataFrame from the CSV content
        df = pd.read_csv(StringIO(csv_content))

        # Add a 'game_date' column
        df['game_date'] = game_date

        # Convert the current time to Eastern Time and add an 'added_ts' column
        eastern = pytz.timezone('US/Eastern')
        added_ts = datetime.now(eastern).strftime('%Y-%m-%d %H:%M:%S')

        # Rename and reorder columns
        df = df.rename(columns={'name': 'player_id', 'time': 'game_time'})
        df['player_id'] = df['player_id'].str.lower()
        df = df[['game_date', 'player_id', 'game_time']]

        # Append the DataFrame to the combined DataFrame
        combined_df = pd.concat([combined_df, df], ignore_index=True)

    # add timestamp
    combined_df['added_ts'] = added_ts
    combined_df.to_csv('files/mini_backup.csv', index=False)

    engine = create_engine(sql_addr)
    combined_df.to_sql('mini_history', engine, if_exists='append', index=False)

    print("ok, done")
else:
    print(f"Failed to fetch the URL. Status code: {response.status_code}")
