import logging, socket, pytz
from datetime import datetime

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(f"files/bot_{socket.gethostname()}.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s ... %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(file_handler)

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
