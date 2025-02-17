import os, socket
from dotenv import load_dotenv
import json
import zipfile
import platform

def load_env_variables():
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

    return SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA, NYT_COOKIE

def get_sql_address(SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA):
    # Construct the SQL address string using the variables
    sql_addr = f"mysql+pymysql://{SQLUSER}:{SQLPASS}@{SQLHOST}:{SQLPORT}/{SQLDATA}"
    return sql_addr

def get_db_config(SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA):
    # Define db_config using the variables
    db_config = {
        'host': SQLHOST,
        'port': SQLPORT,
        'user': SQLUSER,
        'password': SQLPASS,
        'db': SQLDATA
    }
    return db_config

def get_test_mode():
    # Check the operating system
    if platform.system().lower() in ['linux', 'unix']:
        return False
    else:
        return True

def load_carrier_emails():
    # load mobile carrier emails
    sms_carriers_path = 'files/config/carriers.json'
    with open(sms_carriers_path, 'r') as file:
        carrier_emails = json.load(file)
    return carrier_emails

# Load environment variables
SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA, NYT_COOKIE = load_env_variables()

# Get SQL address
sql_addr = get_sql_address(SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA)

# Get DB config
db_config = get_db_config(SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA)

# Get test mode
test_mode = get_test_mode()

# Load carrier emails
carrier_emails = load_carrier_emails()