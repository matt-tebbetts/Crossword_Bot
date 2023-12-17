import os, socket
from dotenv import load_dotenv
import json

# Load environment variables from a .env file
load_dotenv()

# Retrieve environment variables
SQLUSER = os.getenv('SQLUSER')
SQLPASS = os.getenv('SQLPASS')
SQLHOST = os.getenv('SQLHOST')
SQLPORT = int(os.getenv('SQLPORT'))
SQLDATA = os.getenv('SQLDATA')
NYT_COOKIE = os.getenv('NYT_COOKIE')

# Check if all environment variables were found
for var in [SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA]:
    if var is None:
        raise ValueError(f"Environment variable '{var}' not found.")

# Construct the SQL address string using the variables
sql_addr = f"mysql+pymysql://{SQLUSER}:{SQLPASS}@{SQLHOST}:{SQLPORT}/{SQLDATA}"

# Define db_config using the variables
db_config = {
    'host': SQLHOST,
    'port': SQLPORT,
    'user': SQLUSER,
    'password': SQLPASS,
    'db': SQLDATA
}

# set test_mode if on desktop
test_mode = True if 'desktop' in str.lower(socket.gethostname()) else False

# load mobile carrier emails
with open('files/config/carriers.json', 'r') as file:
    carrier_emails = json.load(file)