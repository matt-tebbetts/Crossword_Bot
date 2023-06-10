import os
import re
import json
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import discord
import asyncio

# secrets
load_dotenv()
YOUTUBE_CLIENT_SECRET = json.loads(os.getenv('YOUTUBE_CLIENT_SECRET'))
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
YOUTUBE_URL_REGEX = r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/\S+'


def youtube_auth():
    flow = InstalledAppFlow.from_client_config(YOUTUBE_CLIENT_SECRET, YOUTUBE_SCOPES)
    return flow.run_console()


def create_youtube_playlist(youtube, title, description):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return response['id']


def add_video_to_playlist(youtube, playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    request.execute()


def extract_video_ids(youtube_links):
    video_ids = []
    for link in youtube_links:
        video_id = None
        if 'youtu.be' in link:
            video_id = link.split('/')[-1]
        elif 'youtube.com' in link:
            video_id = re.search(r'v=([^&]+)', link).group(1)
        
        if video_id:
            video_ids.append(video_id)
    return video_ids


def get_youtube_video_title(youtube, video_id):
    request = youtube.videos().list(
        part='snippet',
        id=video_id
    )
    response = request.execute()
    items = response.get('items', [])
    if items:
        return items[0]['snippet']['title']
    return ""


async def get_discord_history(client, channel_id):
    channel = client.get_channel(channel_id)
    youtube_links = []
    youtube_titles = []
    added_by = []
    urls_found_in_thread = 0  # Counter for URLs found
    async for message in channel.history(limit=1000):
        match = re.search(YOUTUBE_URL_REGEX, message.content)
        if match:
            youtube_links.append(match.group())
            youtube_titles.append("")
            added_by.append(message.author.name)
            urls_found_in_thread += 1  # Increment the counter

    if not youtube_links:
        print("No YouTube links found in the Discord chat history.")
        return [], [], []

    return youtube_links, youtube_titles, added_by



async def create_playlist_from_discord_history(client, channel_id, playlist_title, playlist_description):
    youtube_links, youtube_titles, added_by = await get_discord_history(client, channel_id)
    if not youtube_links:
        print("No YouTube links found in the Discord chat history.")
        return

    youtube = build('youtube', 'v3', credentials=youtube_auth())
    playlist_id = create_youtube_playlist(youtube, playlist_title, playlist_description)

    video_ids = extract_video_ids(youtube_links)
    for i, video_id in enumerate(video_ids):
        try:
            print(f"Attempting to add video with ID {video_id} to the playlist.")  # Added print statement
            add_video_to_playlist(youtube, playlist_id, video_id)
            print(f"Added video with ID {video_id} to the playlist.")
            youtube_titles[i] = get_youtube_video_title(youtube, video_id) 
        except HttpError as error:
            print(f"An error occurred while adding video with ID {video_id} to the playlist: {error}")

    playlist_data = {
        'youtube_url': youtube_links,
        'youtube_title': youtube_titles,
        'added_by': added_by
    }
    df = pd.DataFrame(playlist_data)

    # Export DataFrame to CSV file
    csv_filename = 'files/youtube_playlist.csv'
    df.to_csv(csv_filename, index=False)
    print(f"Playlist created with ID {playlist_id}.")
    print(f"Playlist data exported to {csv_filename}")


if __name__ == "__main__":
    # discord connection
    my_intents = discord.Intents.all()
    my_intents.message_content = True
    client = discord.Client(intents=my_intents)
    @client.event

    async def on_ready():
        print('Bot is ready.')
        # This is where we call the function.
        # Make sure to replace with your actual values
        channel_id = 1072246720580296736
        playlist_title = 'My Playlist Test 1'  # Replace with your playlist title
        playlist_description = 'This is my playlist.'  # Replace with your playlist description
        await create_playlist_from_discord_history(client, channel_id, playlist_title, playlist_description)

    token = os.getenv('CROSSWORD_BOT')
    client.run(token)
