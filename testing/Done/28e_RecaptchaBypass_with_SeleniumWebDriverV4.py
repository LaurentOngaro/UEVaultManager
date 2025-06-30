# coding=utf-8
"""
2025-06-24
TESTED: This script works as expected.
The browser is visible , the page is loaded, the recaptcha is bypassed and the text 'Ninja Combat' is found
TIME TO LOAD THE PAGE (with NO headless) : 5.17 seconds
TIME TO LOAD THE PAGE (with headless) : 2.03 seconds
"""

# install official package by running the following command in the terminal
# pip install seleniumbase

from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
import time

start_time: float = time.time()

url = "https://www.unrealengine.com/marketplace/en-US/product/ninja-combat"

service = ChromeService(executable_path=r"C:\Program Files\Chromium\Application\chrome.exe")
options = webdriver.ChromeOptions()
# options.page_load_strategy = 'eager'
# more info on options : https://github.com/GoogleChrome/chrome-launcher/blob/main/docs/chrome-flags-for-tools.md
# options.add_argument('--headless')  # Run in headless mode (uncomment to enable)- CAPTCHA will not be solved in headless mode
options.add_argument('--no-sandbox')  # Bypass OS security model
options.add_argument('--window-position=0,0')
options.add_argument('--window-size=200,200')
options.add_argument('--window-name="UndetectedChrome"')
options.add_argument('--no-first-run')
options.add_argument('--no-experiments')
options.add_argument('--enable-gpu')
options.add_argument('--disable-sync')
options.add_argument('--enable-automation')
options.add_argument('--disable-client-side-phishing-detection')  # Disables client-side phishing detection
options.add_argument('--disable-component-extensions-with-background-pages')  # Disable some built-in extensions that aren't affected
options.add_argument('--disable-default-apps')  # Disable installation of default apps
options.add_argument('--disable-extensions')  # Disable all chrome extensions
options.add_argument('--disable-features=InterestFeedContentSuggestions')  # Disables the Discover feed on NTP
options.add_argument('--disable-features=Translate')  # Disables Chrome translation,
options.add_argument('--hide-scrollbars')  # Hide scrollbars from screenshots.
options.add_argument('--mute-audio')  # Mute any audio
options.add_argument('--no-default-browser-check')  # Disable the default browser check, do not prompt to set it as such
options.add_argument('--no-first-run')  # Skip first run wizards
options.add_argument('--ash-no-nudges')  # Avoids blue bubble "user education" nudges (eg., "… give your browser a new look", Memory Saver)
options.add_argument('--disable-search-engine-choice-screen')  # Disable the 2023+ search engine choice screen
options.add_argument('--propagate-iph-for-testing')
options.add_argument('--disable-features=MediaRouter')
driver = webdriver.Chrome(options)

print(f'Opening {url}')
driver.get(url)
# content = driver.page_source  # Get the HTML of the current page.
# print(content)
try:
    title = driver.find_element(By.TAG_NAME, "H1")
    is_ok = 'Ninja Combat' in title.text
    print(f'RESULT CAPTCHA BYPASSED: {is_ok}')
except NoSuchElementException:
    print('Incorrect login/password')

print(f'Time taken: {time.time() - start_time:.2f}')
driver.quit()
print('Browser closed')
