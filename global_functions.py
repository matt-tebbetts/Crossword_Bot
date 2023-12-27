import logging
import socket
import pytz
import os
from datetime import datetime
import stat
import json
from config import test_mode

def set_logger():
    # Logger configuration
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Log file path configuration
    log_directory = "files/logs"
    log_file = f"{log_directory}/{socket.gethostname()}.log"

    # Ensure directory exists
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
        os.chmod(log_directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)  # chmod 775 for directory

    # Create the log file if it doesn't exist and set permissions
    if not os.path.exists(log_file):
        open(log_file, 'a').close()  # Create the file if it does not exist
        os.chmod(log_file, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)  # chmod 744: rwx for user, r for group and others

    # File handler configuration for logger
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(message)s")) # removed timestamp
    
    logger.addHandler(file_handler)
    return logger

# Use the function
logger = set_logger()

# get now
def get_now():
    return datetime.now(pytz.timezone('US/Eastern'))

# get current time
def get_current_time(ms=False):
    now = get_now()
    if ms:
        return now.strftime("%Y-%m-%d %H:%M:%S.%f")
    else:
        return now.strftime("%Y-%m-%d %H:%M:%S")

# get current date
def get_date():
    return datetime.now(pytz.timezone('US/Eastern'))

# get last hour before expiration
def get_cutoff_hour():
    return 18 if get_date().weekday() in [5, 6] else 22

# get last hour before expiration
def get_final_hour():
    return get_cutoff_hour() - 1

# function to both print messages and save them to the log file
def bot_print(message):
    
    # add timestamp to message
    msg = f"{get_current_time(ms=True)}: {message}"
    
    # print and log message
    if test_mode:
        print(msg)
    else:
        print(message)
    
    # save to logger with timestamp
    logger.info(msg)

# read json
def read_json(filepath, default_data=[]):

    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(filepath, 'w') as file:
            json.dump(default_data, file)
        return default_data

# write json
def write_json(filepath, data):
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)