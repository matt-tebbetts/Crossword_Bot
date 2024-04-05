import os
from dotenv import load_dotenv
import tweepy

# Load environment variables
load_dotenv()
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# Initialize Tweepy client with Bearer Token
client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

# id text filepath
id_text_filepath = "last_processed_id.txt"

# Load the last processed ID
try:
    with open(id_text_filepath, "r") as file:
        last_processed_id = int(file.read().strip())
except FileNotFoundError:
    last_processed_id = 1  # Default if file doesn't exist

# Define your search query
query = "Wordle" # -filter:retweets"

# Fetch new tweets
tweets = client.search_recent_tweets(query=query, max_results=10, since_id=last_processed_id)

# Assume no new tweets initially
new_last_processed_id = last_processed_id

if tweets.data:
    for tweet in tweets.data:
        # Process each tweet here
        print(tweet.text)

        # Update the highest ID seen so far
        new_last_processed_id = max(new_last_processed_id, tweet.id)

# Update the last processed ID file
with open(id_text_filepath, "w") as file:
    file.write(str(new_last_processed_id))
