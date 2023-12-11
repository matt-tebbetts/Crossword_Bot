import logging, socket, pytz, os
from datetime import datetime
import stat

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
    file_handler.setFormatter(logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    
    logger.addHandler(file_handler)
    return logger

# Use the function
logger = set_logger()

# get current time
def get_current_time(ms=False):
    now = datetime.now(pytz.timezone('US/Eastern'))
    if ms:
        return now.strftime("%Y-%m-%d %H:%M:%S.%f")
    else:
        return now.strftime("%Y-%m-%d %H:%M:%S")

# function to both print messages and save them to the log file
def bot_print(message):
    
    # add timestamp to message
    msg = f"{get_current_time(ms=True)}: {message}"
    
    # print and log message
    print(msg)
    logger.info(msg)
