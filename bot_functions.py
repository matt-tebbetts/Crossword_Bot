# connections
import os
from dotenv import load_dotenv
from global_functions import *

# data management
import json
import pandas as pd
import pytz
import re
from datetime import date, datetime, timedelta
from dateutil.parser import parse

# internal
import bot_camera
from bot_sql import get_df_from_sql, send_df_to_sql

# get secrets
load_dotenv()
NYT_COOKIE = os.getenv('NYT_COOKIE')

# find main channel id for each guild (old)
async def get_bot_channels():
    query = """
        SELECT guild_id, channel_id, guild_channel_category
        FROM discord_connections
        WHERE guild_channel_category = 'main'
    """
    
    # Get the DataFrame from the SQL query
    df = await get_df_from_sql(query)

    # Initialize bot_channels dictionary
    bot_channels = {}

    # Iterate over DataFrame rows and populate the dictionary
    for index, row in df.iterrows():
        bot_channels[row["guild_id"]] = {
            "channel_id": row["channel_id"],
            "channel_id_int": int(row["channel_id"]),
        }

    return bot_channels

# get mini date
def get_mini_date():

    # if past cutoff hour, use tomorrow's date
    if get_now().hour >= get_cutoff_hour():
        return (get_date() + timedelta(days=1)).date()
    else:
        return get_date()

# find users who haven't completed the mini
async def mini_not_completed():
    df = await get_df_from_sql("SELECT * FROM matt.mini_not_completed")
    return df

# translate date range based on text
def get_date_range(user_input):
    today = datetime.now(pytz.timezone('US/Eastern')).date()

    # Helper function to parse date string and set year to current year if not provided
    def parse_date(date_str, default_year=today.year):
        date_obj = parse(date_str)
        if date_obj.year == 1900:  # dateutil's default year is 1900 when not provided
            date_obj = date_obj.replace(year=default_year)
        return date_obj.date()

    try:
        if user_input == 'today':
            min_date = max_date = today
        elif user_input == 'yesterday':
            min_date = max_date = today - timedelta(days=1)
        elif user_input == 'last week':
            min_date = today - timedelta(days=today.weekday(), weeks=1)
            max_date = min_date + timedelta(days=6)
        elif user_input == 'this week':
            min_date = today - timedelta(days=today.weekday())
            max_date = today # - timedelta(days=1)
        elif user_input == 'this month':
            min_date = today.replace(day=1)
            max_date = today # - timedelta(days=1)
        elif user_input == 'last month':
            min_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            max_date = (min_date.replace(month=min_date.month % 12 + 1) - timedelta(days=1))
        elif user_input == 'this year':
            min_date = today.replace(month=1, day=1)
            max_date = today # - timedelta(days=1)
        elif user_input == 'last year':
            min_date = today.replace(year=today.year - 1, month=1, day=1)
            max_date = today.replace(year=today.year - 1, month=12, day=31)
        elif user_input == 'all time':
            min_date = date.min
            max_date = date.max
        else:
            dates = [parse_date(d.strip()) for d in user_input.split(':')]
            min_date, max_date = (dates[0], dates[-1]) if len(dates) > 1 else (dates[0], dates[0])

    except(ValueError, TypeError):
        return None
    
    return min_date, max_date

# returns image location of leaderboard
async def get_leaderboard(guild_id='Global', game_name=None, min_date=None, max_date=None, user_nm=None):
    from bot_queries import build_query

    today = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")

    # if no date range, use default
    if min_date is None and max_date is None:
        if game_name == 'mini':
            min_date = max_date = get_mini_date().strftime("%Y-%m-%d")
        else:
            min_date, max_date = today, today
    else:
        min_date = min_date.strftime("%Y-%m-%d")
        max_date = max_date.strftime("%Y-%m-%d")
    
    # format the title
    if min_date == max_date:
        title_date = min_date
    else:
        title_date = f"{min_date} through {max_date}"

    # determine leaderboard query to run
    cols, query, params = build_query(guild_id, game_name, min_date, max_date, user_nm)
    
    try:
        # new asynchronous query function
        df = await get_df_from_sql(query, params)

    except Exception as e:
        bot_print(f"Error when trying to run SQL query: {e}")
        img = 'files/images/error.png'
        return img

    # if leaderboard empty
    if len(df) == 0 or not cols:
        bot_print('The leaderboard is empty')
        img = 'files/images/error.png' # should return a blank image or something...
        return img

    df.columns = cols
    # clean some columns
    if 'Rank' in df.columns:
        df['Rank'] = df['Rank'].fillna('').astype(str).apply(lambda x: x.rstrip('.0') if '.' in x and x != '' else x)
    if 'Game' in df.columns:
        df['Game'] = df['Game'].str.capitalize()

    # create image
    img_title = game_name.capitalize() if game_name != 'my_scores' else user_nm

    # try to generate image
    try:
        img = bot_camera.dataframe_to_image_dark_mode(df, img_title=img_title, img_subtitle=title_date)
    except Exception as e:
        bot_print(f"Error when trying to generate image: {e}")
        img = 'files/images/error.png'

    return img

# find game type
async def get_scoring_type(game_name=None):
    query = """select distinct scoring_type from game_details where game_name = %s"""
    params = (game_name,)
    df = await get_df_from_sql(query, params=params)
    return df['scoring_type'].values[0]

# get score from message
async def extract_score(message_text, game_name):
    scoring_type = await get_scoring_type(game_name)
    bonuses = {}

    game = game_name.lower()

    if game == "connections":
            
        # analyze line squares
        lines = message_text.strip().split("\n")
        guesses_taken = len([line for line in lines if any(emoji in line for emoji in ["🟨", "🟩", "🟦", "🟪"])])
        completed_lines = 0

        # Calculate metric_01 based on the second line of the message
        metric_01 = 1 if lines[1].count("🟪") == 4 else 0

        # count completed categories
        for line in lines[1:]:  # Start from the second line
            if len(set(line)) == 1 and line.strip() != "":
                completed_lines += 1

        rainbow_bonus = len(set(lines[2])) == 4
        purple_bonus = lines[3].count("🟪") == 4

        score = f"{guesses_taken}/7" if completed_lines == 4 else "X/7"
        bonuses = {'rainbow_bonus': rainbow_bonus, 'purple_bonus': purple_bonus}
    
    elif game == 'crosswordle':
        # Check for minutes and seconds format first
        match = re.search(r"(\d+)m\s*(\d+)s", message_text)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
        else:
            # If not found, look for seconds only
            match = re.search(r"(\d+)s", message_text)
            if match:
                seconds = int(match.group(1))
                minutes = 0

        # Format the score as "minutes:seconds"
        if match:  # Check if either pattern was found
            score = f"{minutes}:{str(seconds).zfill(2)}"

    elif game == 'boxoffice':
        pattern = re.compile(r'🏆\s*(\d+)')
        match = pattern.search(message_text)
        score = match.group(1) if match else None

    elif game == 'travle':
        # travle now prints out like this, so scrape the "+0" as the score: #travle #485 +0
        parts = message_text.split()
        score = parts[2] if len(parts) > 2 else None

    elif game == 'octordle' or game == 'octordle_sequence' or game == 'octordle_rescue':
        
        # get second element from last line (i.e. "Score: 87")
        score = int(message_text.split('\n')[-1].split(' ')[1])
        
        # calculate bonus
        red_square_emojis = message_text.count('🟥')
        bonuses = {'correct_guesses': (8 - red_square_emojis)}

    else:
        if scoring_type == "guesses":
            pattern = re.compile(r'(\d{1,2}|\?|X)/\d{1,2}')

        elif scoring_type == "points":
            pattern = re.compile(r'(\d{1,3}(?:,\d{3})*)(?=/)')
            
        elif scoring_type == "timed":
            pattern = re.compile(r'\d{1,2}:\d{2}')
        
        match = pattern.search(message_text)
        if match:           
            if game_name.lower() == 'timeguessr':
                score = match.group(1).replace(',', '')
            else:
                score = match.group(0)
        
    return {'score': score, 'bonuses': bonuses}

# add discord scores to database when people paste them to discord chat
async def add_score(game_name, game_date, discord_id, msg_txt):

    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    added_ts = now.strftime("%Y-%m-%d %H:%M:%S")

    # set these up
    game_name = game_name
    game_score = None
    game_dtl = None
    metric_01 = None
    metric_02 = None # game completed yes/no
    metric_03 = None

    # find game_score from message details
    score_details = await extract_score(msg_txt, game_name)
    game_score = score_details.get('score')
    bonuses = score_details.get('bonuses')


    # game detail for certain games
    if game_name == 'boxoffice':
        game_dtl = msg_txt.strip().split("\n")[1] # movie date
        metric_01 = msg_txt.count("✅") # movies guessed
    elif game_name.lower() == 'connections':
        lines = msg_txt.strip().split("\n")
        metric_01 = 1 if lines[2].count("🟪") == 4 else 0

    # put into dataframe
    my_cols = ['game_date', 'game_name', 'game_score', 'added_ts', 'discord_id', 'game_dtl', 'metric_01', 'metric_02', 'metric_03']
    my_data = [[game_date, game_name, game_score, added_ts, discord_id, game_dtl, metric_01, metric_02, metric_03]]
    df = pd.DataFrame(data=my_data, columns=my_cols)

    # send to sql using new function
    await send_df_to_sql(df, 'game_history', if_exists='append')

    msg_back = f"Added Score: {game_date}, {game_name}, {discord_id}, {game_score}"
    bot_print(msg_back)

    return {'message': msg_back, 'bonuses': bonuses}

# save message to file
def save_message_detail(message):
    
    # Find URLs
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
    
    # Check for GIFs or other attachments
    attachments = [attachment.url for attachment in message.attachments]
    urls.extend(attachments)
    contains_gifs = any(url.endswith('.gif') for url in attachments)
    
    msg_crt = message.created_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")
    msg_edt = None
    if message.edited_at is not None:
        msg_edt = message.edited_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # Structure data
    message_data = {
        "id": message.id,
        "content": message.content,
        "create_ts": msg_crt,
        "edit_ts": msg_edt,
        "length": len(message.content),
        "author_id": message.author.id,
        "author_nm": message.author.name,
        "author_nick": message.author.nick,
        "channel_id": message.channel.id,
        "channel_nm": message.channel.name,
        "has_attachments": bool(message.attachments),
        "has_links": bool(urls),
        "has_gifs": bool(contains_gifs),
        "has_mentions": bool(message.mentions),
        "list_of_attachment_types": [attachment.content_type for attachment in message.attachments],
        "list_of_links": urls,
        "list_of_gifs": [url for url in urls if url.endswith('.gif')],
        "list_of_mentioned": [str(user.name) for user in message.mentions]
    }

    # set directory to save messages
    file_path = f"files/guilds/{message.guild.name}/messages.json"

    # Read existing messages (if any)
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            content = file.read()
            if content:  # Check if the file is not empty
                try:
                    messages = json.loads(content)
                except json.JSONDecodeError as e:
                    bot_print(f"JSON decode error: {e}")
                    # Handle the error - maybe backup the file and create a new empty dictionary
                    messages = {}
            else:
                messages = {}
    else:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        messages = {}

    messages[message.id] = message_data  # This will overwrite if the ID already exists

    # Write updated messages back to the file
    with open(file_path, 'w') as file:
        json.dump(messages, file, indent=4)

    ## write contents to sql
    # df = pd.DataFrame(data=[message_data])
    # await send_df_to_sql(df, 'guild_messages', if_exists='append')

    return

# get users from a channel
def get_users(bot):

    # loop through guilds
    user_details = {}
    for guild in bot.guilds:
        for member in guild.members:
            member_nm = str(member)[:-2] if str(member).endswith("#0") else str(member)
            user_details[member_nm] = {
                "member_nm": member_nm,
                "member_id": str(member.id),
                "guild_nm": guild.name,
                "guild_id": str(guild.id),
                "joined_ts": member.joined_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S"),
                "is_bot": member.bot,
                "is_admin": member.guild_permissions.administrator,
                "nickname": member.nick,
                "roles": [role.name for role in member.roles],
                "status": str(member.status)
            }
    
        # save to file
        users_json = f"files/guilds/{guild.name}/users.json"        # file path
        os.makedirs(os.path.dirname(users_json), exist_ok=True)     # if not exists, create the directory
        with open(users_json, 'w') as file:                         # open (and create, if not exists) the file
            json.dump(user_details, file, indent=4)                 # overwrite the file with the new user details
    
    return

# save mini leaders
async def check_mini_leaders():

    # use get_df_from_sql to get the latest leaders
    query = """
        select 
            guild_nm,
            player_name,
            game_time
        from mini_view
        where game_date = (select max(game_date) from mini_view)
        and game_rank = 1
    """

    try:
        df = await get_df_from_sql(query)
    except Exception as e:
        bot_print(f"Error in check_mini_leaders! Error when trying to run SQL query: {e}")
        return

    # get leaders by guild
    aggregated_df = df.groupby('guild_nm')['player_name'].apply(list).reset_index()
    new_leaders = aggregated_df.to_dict(orient='records')

    # loop through guilds and check for differences
    guild_differences = {}
    for guild in new_leaders:
        guild_name = guild['guild_nm']

        # ignore global guild
        if guild_name == "Global":
            continue

        # get list of previous leaders
        leader_filepath = f"files/guilds/{guild_name}/leaders.json"
        previous_leaders = read_json(leader_filepath)

        # check if new leaders are different
        if set(guild['player_name']) != set(previous_leaders):

            # overwrite with new leaders
            write_json(leader_filepath, guild['player_name'])

            # set guild_differences to True
            guild_differences[guild_name] = True
    
        else:
            
            # set guild_differences to False
            guild_differences[guild_name] = False
    
    return guild_differences