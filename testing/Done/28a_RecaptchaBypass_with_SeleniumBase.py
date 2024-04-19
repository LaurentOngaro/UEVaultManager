# coding=utf-8
"""
TESTED: This script works as expected.
The browser is visible , the page is loaded, the recaptcha is bypassed and the text 'Ninja Combat' is found
TIME TO LOAD THE PAGE (with headless2=False) : 9.5 seconds
TIME TO LOAD THE PAGE (with headless2=True) : 12,82 seconds

NOTE: sometimes the page closes BEFORE getting the content and the process enter into an infinite loop
"""

# install official package by running the following command in the terminal
# pip install seleniumbase

from seleniumbase import Driver

import time

start_time: float = time.time()
url = "https://www.unrealengine.com/marketplace/en-US/product/ninja-combat"
print(f'Opening {url}')
driver = Driver(
    uc=True,  #
    binary_location=r"C:\Program Files\Chromium\Application\chrome.exe",  #
    headless2=True,  # Enable headless mode will slow down the loading of the page (+30%)
    undetectable=True,  #
    block_images=True,  # Block images from loading
    enable_sync=False,  # Disable the Chrome Sync feature
    enable_3d_apis=False,  # Disable 3D APIs
)
driver.uc_open_with_reconnect(url, 3)
content = driver.get_page_source()  # Get the HTML of the current page.
# print(content)
is_ok = driver.is_text_visible('Ninja Combat', 'H1')  # Return text visibility.
print(f'RESULT CAPTCHA BYPASSED: {is_ok}')
print(f'Time taken: {time.time() - start_time:.2f}')
driver.close()
driver.quit()
