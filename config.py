import os, socket
from dotenv import load_dotenv
import json
import requests
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
    # set test_mode if on desktop
    keywords = ['desktop', 'mjt']
    hostname = str.lower(socket.gethostname())
    print('Hostname:', hostname)
    test_mode = any(keyword in hostname for keyword in keywords)
    return test_mode

def load_carrier_emails():
    # load mobile carrier emails
    sms_carriers_path = 'files/config/carriers.json'
    with open(sms_carriers_path, 'r') as file:
        carrier_emails = json.load(file)
    return carrier_emails

def check_chromedriver():
    try:
        print("Checking for ChromeDriver...")

        # Define the platform key based on the current platform
        platform_key = 'linux64' if platform.system().lower() == 'linux' else 'win32'

        # Define the directory where the driver will be downloaded
        download_dir = 'files/config/chromedriver-' + platform_key + '/'

        # Check if the driver is already downloaded
        if not os.path.exists(download_dir + 'chromedriver'):
            print("ChromeDriver not found. Downloading...")

            # Get the latest driver version
            response = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE')
            latest_version = response.text.strip()

            # Get the driver data
            response = requests.get('https://api.github.com/repos/rosolimo/chromedriver')
            data = response.json()
            latest_version_data = data['versions'][0]

            # Find the driver download URL
            download_url = None
            for download in latest_version_data['downloads']['chrome']:
                if download['platform'] == platform_key:
                    download_url = download['url']
                    break

            # Download the driver
            if download_url:
                print("Download URL found. Downloading ChromeDriver...")
                response = requests.get(download_url)
                with open(download_dir + 'chromedriver.zip', 'wb') as f:
                    f.write(response.content)

                # Extract the driver
                print("Extracting ChromeDriver...")
                with zipfile.ZipFile(download_dir + 'chromedriver.zip', 'r') as zip_ref:
                    zip_ref.extractall(download_dir)

                # Remove the zip file
                print("Removing zip file...")
                os.remove(download_dir + 'chromedriver.zip')
            else:
                print("Download URL not found.")
        else:
            print("ChromeDriver already exists.")
    except Exception as e:
        print(f"An error occurred while checking for ChromeDriver: {e}")

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

# Check chromedriver installation
check_chromedriver()