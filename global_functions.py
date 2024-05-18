import logging
import socket
import pytz
import os
from datetime import datetime
import stat
import json
from config import *
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
import zipfile
import platform

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

# get now as datetime
def get_now():
    return datetime.now(pytz.timezone('US/Eastern'))

# get current date as date, not datetime
def get_today():
    return get_now().date()

# get now as string
def get_current_time(ms=False):
    now = get_now()
    if ms:
        return now.strftime("%Y-%m-%d %H:%M:%S.%f")
    else:
        return now.strftime("%Y-%m-%d %H:%M:%S")

# get current date
def get_date():
    return datetime.now(pytz.timezone('US/Eastern'))

# get hour of expiration
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

def save_html_to_file(url, file_name):

    # set up chromedriver
    sys = "win64" if test_mode else "linux64"
    driver_path = f"files\config\chromedriver-{sys}"
    extension = ".exe" if platform.system().lower() == 'windows' else ""
    service = Service(executable_path=f"{driver_path}\chromedriver{extension}")
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)

    # use chromedriver + soup
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    pretty_html = soup.prettify()
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(pretty_html)
    
    driver.quit()
    bot_print(f"HTML saved from {url} to {file_name}")

def check_chromedriver():
    try:
        bot_print("Checking for ChromeDriver...")

        # Define the platform key based on the current platform
        platform_key = 'linux64' if platform.system().lower() == 'linux' else 'win64'
        extension = ".exe" if platform.system().lower() == 'windows' else ""

        # Define the directory where the driver will be downloaded
        download_dir = 'files/config'
        full_file_nm = f"{download_dir}/chromedriver-{platform_key}/chromedriver{extension}"

        # Check if the driver is already downloaded
        if not os.path.exists(full_file_nm):
            bot_print(f"ChromeDriver not found in {download_dir}. Downloading...")

            # Get the driver data
            response = requests.get('https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json')
            
            # Parse the response data
            data = response.json()

            # Sort the versions in descending order
            sorted_versions = sorted(data['versions'], key=lambda v: v['version'], reverse=True)

            # Get the latest version
            latest_version_data = sorted_versions[0]

            # Find the driver download URL
            download_url = None
            for download in latest_version_data['downloads']['chromedriver']:
                if download['platform'] == platform_key:
                    download_url = download['url']
                    break

            # Download the driver
            if download_url:
                bot_print("Download URL found. Downloading ChromeDriver...")
                response = requests.get(download_url)
                with open(download_dir + 'chromedriver.zip', 'wb') as f:
                    f.write(response.content)

                # Extract the driver
                bot_print("Extracting ChromeDriver...")
                with zipfile.ZipFile(download_dir + 'chromedriver.zip', 'r') as zip_ref:
                    zip_ref.extractall(download_dir)

                # Remove the zip file
                bot_print("Removing zip file...")
                os.remove(download_dir + 'chromedriver.zip')
            else:
                bot_print("Download URL not found.")
        else:
            bot_print("ChromeDriver already exists.")
    except Exception as e:
        bot_print(f"An error occurred while checking for ChromeDriver: {e}")
        bot_print(f"Exception type: {type(e)}")
        bot_print("Traceback:")
        bot_print(traceback.format_exc())