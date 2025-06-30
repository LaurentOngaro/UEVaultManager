# coding=utf-8
"""
AFTER 2025:
TESTED: This script DOES NOT work as expected.
The browser is visible , the page is loaded, the recaptcha is NOT bypassed and the text 'Ninja Combat' is NOT found


BEFORE 2025:
TESTED: This script works as expected.
The browser is visible , the page is loaded, the recaptcha is bypassed and the text 'Ninja Combat' is found
TIME TO LOAD THE PAGE: 2 seconds
"""

# install official package by running the following command in the terminal
# pip install undetected-chromedriver
# install my personal fork by running the following command in the terminal
# my fork fix option to resize the windows and an error at the end of the execution
# pip install -e git+https://github.com/LaurentOngaro/F_undetected-chromedriver#egg=undetected-chromedriver

import nodriver as uc
import time
import os

url = "https://www.unrealengine.com/marketplace/en-US/product/ninja-combat"
window_width = 1024
window_height = 768
# note:  the window position could be OUTSIDE the viewable area and its works !!
window_left = -window_width
window_top = -window_height
window_left = 0
window_top = 0

start_time: float = time.time()
print(f'Opening {url}')
params = {}

browser_path = r"C:\Program Files\Chromium\Application\chrome.exe"

params["headless"] = False  # True  will not bypass the captcha
params["use_subprocess"] = True  # False will crash the script
params["browser_executable_path"] = browser_path
params["user_multi_procs"] = True  # will speed up the process
params['browser_args'] = [
    f'--window-size={window_width},{window_height}',  # set the initial size of the window
    f'--window-position={window_left},{window_top}',  # set the initial position of the window
    '--window-name="UndetectedChrome"',  # set the name of the window
    '--no-first-run',
    '--no-default-browser-check',
    '--no-experiments',
    '--mute-audio',
    '--enable-gpu',
    '--disable-extensions',
    # next options have been tested and are OK
    #'--start-maximized', # debug only
    #'--incognito',

    # next options have been tested and could create issue
    # '--no-sandbox',  # needed for linux

    # next options have been tested and CAUSE AN ERROR
    #'--headless',
    #'--silent-launch',
]
params["content"] = ""


async def uc_get_content(url, params={}):
    browser = await uc.start(**params)
    page = await browser.get(url)
    await page.activate()
    # set the size of the window AFTER the page is loaded
    # await page.set_window_size(window_left, window_top, window_width, window_height)
    await page.minimize()
    params["content"] = await page.get_content()


uc.loop().run_until_complete(uc_get_content(url, params))

page_content = params["content"]
# print(page_content)
# TODO: use beautifulsoup to parse the page content
# check if page_content contains the text 'Ninja Combat'
is_ok = 'Ninja Combat' in page_content
print(f'RESULT CAPTCHA BYPASSED: {is_ok}')
print(f'Time taken: {time.time() - start_time:.2f}')
