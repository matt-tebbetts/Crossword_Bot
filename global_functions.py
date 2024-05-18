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

def get_os_info():
    os_name = platform.system().lower()
    if os_name == 'linux':
        os_ver = 'linux64'
        os_ext = ''
    elif os_name == 'windows':
        os_ver = 'win64'
        os_ext = '.exe'
    return {'os_name': os_name, 'os_ver': os_ver, 'os_ext': os_ext}

def get_path(app):
    os_info = get_os_info()
    app_folder = f"{app}-{os_info['os_ver']}"
    app_filenm = f"{app}{os_info['os_ext']}"
    path_components = ['files', 'downloads', app_folder, app_filenm]
    path = os.path.join(*path_components)
    return path

def get_webdriver():
    
    # set service
    service = Service(executable_path=get_path('chromedriver'))

    # set options
    options = Options()
    options.binary_location = get_path('chrome')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    return webdriver.Chrome(service=service, options=options)

# check for both chrome and chromedriver
def check_chromedriver():

    os_info = get_os_info()

    for app in ['chromedriver', 'chrome']:
        app_path = get_path(app)

        # Check if already installed
        if os.path.exists(app_path):
            bot_print(f"{app} found")
            continue

        bot_print(f"{app} does not exist")
        try:
            download_dir = "files/downloads"

            # find url for latest driver
            json_url = 'https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json'
            response = requests.get(json_url)
            data = response.json()
            sorted_versions = sorted(data['versions'], key=lambda v: v['version'], reverse=True)
            latest_version_data = sorted_versions[0]
            download_url = None
            for download in latest_version_data['downloads'][f'{app}']:
                if download['platform'] == os_info['os_ver']:
                    download_url = download['url']
                    break

            # Download the driver
            if download_url:
                response = requests.get(download_url)
                with open(download_dir + f'{app}.zip', 'wb') as f:
                    f.write(response.content)

                # Extract the driver
                with zipfile.ZipFile(download_dir + f'{app}.zip', 'r') as zip_ref:
                    zip_ref.extractall(download_dir)
                os.remove(download_dir + f'{app}.zip')
                bot_print(f"{app} installed successfully")

            else:
                bot_print("Download URL not found.")
        
        except Exception as e:
            bot_print(f"An error occurred while checking for ChromeDriver: {e}")
            bot_print(f"Exception type: {type(e)}")
            bot_print("Traceback:")
            bot_print(traceback.format_exc())

def save_html_to_file(url, file_name):
    # use chromedriver + soup
    driver = get_webdriver()
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    pretty_html = soup.prettify()
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(pretty_html)
    
    driver.quit()
    bot_print(f"HTML saved from {url} to {file_name}")
