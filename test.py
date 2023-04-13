from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

options = Options()
options.headless = True
options.add_argument("--window-size=1920,1200")

# Change the path to the Chrome webdriver on your system
driver_path = "C:/Users/matt_/chromedriver.exe"
service = Service(executable_path=driver_path)
driver = webdriver.Chrome(service=service, options=options)

url = "https://public.tableau.com/app/profile/matthew.tebbetts/viz/Mini_16795384393570/Leaderboard?publish=yes"
driver.get(url)

# Give some time for the Tableau Public page to load
driver.implicitly_wait(60)

screenshot_path = "files/images/tableau_screenshot.png"
driver.save_screenshot(screenshot_path)
driver.quit()
