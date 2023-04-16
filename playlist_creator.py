import os
import re
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

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


async def create_playlist_from_discord_history(channel, playlist_title, playlist_description):
    youtube_links = []
    async for message in channel.history(limit=1000):
        links = re.findall(YOUTUBE_URL_REGEX, message.content)
        if links:
            youtube_links.extend(links)

    if not youtube_links:
        print("No YouTube links found in the Discord chat history.")
        return

    youtube = build('youtube', 'v3', credentials=youtube_auth())
    playlist_id = create_youtube_playlist(youtube, playlist_title, playlist_description)

    video_ids = extract_video_ids(youtube_links)
    for video_id in video_ids:
        try:
            print(f"Attempting to add video with ID {video_id} to the playlist.")  # Added print statement
            add_video_to_playlist(youtube, playlist_id, video_id)
            print(f"Added video with ID {video_id} to the playlist.")
        except HttpError as error:
            print(f"An error occurred while adding video with ID {video_id} to the playlist: {error}")

    print(f"Playlist created with ID {playlist_id}.")
