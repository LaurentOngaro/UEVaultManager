# coding=utf-8

# install official package by running the following command in the terminal
# pip install undetected-chromedriver
# install my personal fork by running the following command in the terminal
# my fork fix option to resize the windows and an error at the end of the execution
# pip install -e git+https://github.com/LaurentOngaro/F_undetected-chromedriver#egg=undetected-chromedriver

import undetected_chromedriver as uc
import time
import os

url = "https://www.unrealengine.com/marketplace/en-US/product/ninja-combat"
start_time: float = time.time()
print(f'Opening {url}')

options = uc.ChromeOptions()
options.add_argument("--window-size=1,1")
options.add_argument("--no-sandbox")

try:
    browser_path = uc.find_chrome_executable()
except RuntimeError as e:
    # browser detection will not work if the browsers are not installed as "standard" ones
    print(e)
    browser_path = r"C:\Program Files\Chromium\Application\chrome.exe"
    if os.path.exists(browser_path) and os.access(browser_path, os.X_OK):
        print(f'Using chromium browser in: {browser_path}')

driver = uc.Chrome(
    headless=False,  # True  will not bypass the captcha
    use_subprocess=True,  # False will crash the script
    browser_executable_path=browser_path,
    user_multi_procs=True,  # will speed up the process
    options=options,  # options for the browser
)
try:
    # driver.set_window_position(-3000, 0) # will hide the browser BUT freeze the execution
    # driver.set_window_size(0, 0) # will hide the browser BUT gets bad result
    # driver.minimize_window() # will hide the browser BUT gets bad result
    driver.get(url)
    page_content = driver.page_source
    # print(page_content)
    # TODO: use beautifulsoup to parse the page content
    # check if page_content contains the text 'Ninja Combat'
    is_ok = 'Ninja Combat' in page_content
    print(f'RESULT CAPTCHA BYPASSED: {is_ok}')
    print(f'Time taken: {time.time() - start_time:.2f}')
    driver.close()
    driver.quit()
except Exception as e:
    print(e)
