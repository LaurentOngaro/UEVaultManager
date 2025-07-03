# coding=utf-8
# This script uses Selenium based chrome driver to scrape the FAB Marketplace for asset information based on search keywords.
# It sets up a Chrome WebDriver with specific options, performs searches, and extracts asset details.
# It can use the standard Selenium WebDriver or the 'undetected_chromedriver' for better anti-detection.
# It uses BeautifulSoup to parse the HTML content of the search results.
# The script is designed to run on a Windows machine with a specific Chrome installation path.
import random

#  RESULT TEST 5 : OK (2025-07-03) - all the searches works, but the  delai between each one is 7 to 9s
#  RESULT TEST 1-4 : PARTIAL OK (2025-07-03) - the first search works, but the next ones return a captcha page.
# The FAB Marketplace has implemented a captcha system that prevents automated searches after the first one.

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import undetected_chromedriver as uc
import time

window_width = 1024
window_height = 768
window_left = 2680  # moved to the 3rd screen
window_top = 0
browser_path = r"C:\Program Files\Chromium\Application\chrome.exe"


def chrome_driver_setup(use_uc: bool = True):
    """
    Set up a WebDriver for Chrome with specific options.
    :param use_uc:  If True, uses undetected_chromedriver for better anti-detection.
    :return:  A configured  WebDriver instance for Chrome.
    """
    # NOTE:
    # both undetected_chromedriver and selenium failed to bypass the captcha system of the FAB Marketplace on successive searches.
    if use_uc:
        # Use undetected_chromedriver for better anti-detection
        options = uc.ChromeOptions()
    else:
        # Use standard Selenium WebDriver
        options = webdriver.ChromeOptions()

    options.binary_location = browser_path
    options.add_argument(f'--window-size={window_width},{window_height}')  # set the initial size of the window
    options.add_argument(f'--window-position={window_left},{window_top}')  # set the initial position of the window
    options.add_argument('--window-name="ChromeDriver"')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')  # Disable the default browser check, do not prompt to set it as such
    options.add_argument('--no-experiments')
    options.add_argument('--enable-gpu')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-extensions')  # Disable all chrome extensions
    options.add_argument('--enable-automation')
    options.add_argument('--disable-client-side-phishing-detection')  # Disables client-side phishing detection
    options.add_argument('--disable-component-extensions-with-background-pages')  # Disable some built-in extensions that aren't affected
    options.add_argument('--disable-default-apps')  # Disable installation of default apps
    options.add_argument('--disable-features=InterestFeedContentSuggestions')  # Disables the Discover feed on NTP
    options.add_argument('--disable-features=Translate')  # Disables Chrome translation,
    options.add_argument('--hide-scrollbars')  # Hide scrollbars from screenshots.
    options.add_argument('--mute-audio')  # Mute any audio
    options.add_argument('--no-first-run')  # Skip first run wizards
    options.add_argument('--ash-no-nudges')  # Avoids blue bubble "user education" nudges (e.g. "… give your browser a new look", Memory Saver)
    options.add_argument('--disable-search-engine-choice-screen')  # Disable the 2023+ search engine choice screen
    options.add_argument('--propagate-iph-for-testing')
    options.add_argument('--disable-features=MediaRouter')

    # Anti-detection options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # realistic User agent
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    driver = webdriver.Chrome(options)

    # Hide webdriver properties
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def get_fab_search_data(keyword: str, driver, locale='fr') -> str:
    """
    Extracts and returns the list of asset URLs found for a given keyword on the FAB Marketplace.

    :param keyword: the search string (e.g. "animation starter pack")
    :param driver:  chrome WebDriver instance to use for the search
    :param locale:  language code for the URL (default "fr")
    :return:        A string containing the HTML content of the search results page.
    """
    # Build the search URL
    base_url = f"https://www.fab.com/{locale}/search"
    query = requests.utils.quote(keyword)
    search_url = f"{base_url}?q={query}"

    # Make the HTTP request
    driver.get(search_url)
    return str(driver.page_source)


def analyse_content(content: str, keyword: str, check_name: bool = False, limit: int = 0) -> dict:
    """    Analyse the content of a FAB Marketplace search result page and extract product links.
    :param content:     The HTML content of the page as a string.
    :param keyword:     The search keyword used to filter results.
    :param check_name:  If True, checks if the product name matches the keyword.
    :param limit:       The maximum number of results to return (0 means no limit).
    :return:           A dictionary with product names as keys and their details as values.
    """
    soup = BeautifulSoup(content, "html.parser")
    if not soup:
        print("Error: No content found in the page source.")
        return {}

    # Selection of links to products: href containing '/listings/'
    results = dict()
    index = 0
    found = not check_name
    for a in soup.find_all("a", href=True):
        item = {}
        seller = 'Unknown seller'
        name = f"Unknown asset #{index}"
        href = a["href"]
        if "/listings/" in href:
            try:
                full_url = f"https://www.fab.com{href}"
                # get the fab_id: the last part of the href after the last slash
                fab_id = href.split("/")[-1]
                # get the name: value of the "aria-label" attribute of this link to get its name
                name = a.get("aria-label", name)
                # get the seller: the part after the strings ' par ' or ' by '
                if " par " in name:
                    seller = name.split(" par ")[1]
                    name = name.split(" par ")[0]
                elif " by " in name:
                    seller = name.split(" par ")[1]
                    name = name.split(" by ")[0]

                item['name'] = name
                item['seller'] = seller
                item['fab_id'] = fab_id
                item['url'] = full_url
                results[name] = item
                index += 1

                # if check_name is True, check if the name contains the keyword
                if check_name and keyword.lower() == name.lower():
                    # if the name matches the keyword, return only this item
                    results = {name: item}
                    found = True
                    break

            except Exception as e:
                print(f"Error when extracting the data for the element #{index}: {e!r}")
                continue
        if 0 < limit <= index:
            break
    return results if found else {}


def get_random_user_agent():
    """Returns a random user agent string from a predefined list."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    return random.choice(user_agents)


def change_user_agent(driver, new_user_agent):
    """
    Changes the user agent of the Selenium WebDriver instance.
    :param driver : The Selenium WebDriver instance to modify.
    :param new_user_agent: The new user agent string to set.
    """
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": new_user_agent})


def reset_session_data(driver):
    """
    Resets the session data of the WebDriver instance by clearing cookies, localStorage, sessionStorage, and cache.
    :param driver: The Selenium WebDriver instance to reset.
    """
    try:
        # Supprimer tous les cookies
        driver.delete_all_cookies()

        # Vider le localStorage et sessionStorage
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")

        # Vider le cache (si possible)
        driver.execute_script("window.caches.keys().then(names => { names.forEach(name => { caches.delete(name); }); });")

        print("Session data cleared successfully")

    except Exception as e:
        print(f"Error while cleaning session: {e}")


if __name__ == "__main__":
    keywords = ["animation starter pack", "castle environment", "character controller"]

    test = 5  # Change this value to test different scenarios

    if test == 1:
        print(f"****\nTESTING get_fab_search_data() for a uniq asset with selenium")
        print("Result (2025-07-03): Only the 1st search works, the followings will not return any results because of the appearance of a Captcha !!!")
        chrome_driver = chrome_driver_setup()
        for search in keywords:
            print(f"\nUniq asset that matches '{search}':")
            start_time = time.time()
            assets = analyse_content(get_fab_search_data(search, driver=chrome_driver, locale="fr"), search, check_name=True)
            for key, url in assets.items():
                print(f" - {key} : {url}")
            print(f'Time taken: {time.time() - start_time:.2f}')

    if test == 2:
        print(f"****\nTESTING get_fab_search_data() for a uniq asset with undetected_chromedriver")
        print("Result (2025-07-03): Only the 1st search works, the followings will not return any results because of the appearance of a Captcha !!!")
        chrome_driver = chrome_driver_setup(use_uc=True)
        for search in keywords:
            print(f"\nUniq asset that matches '{search}':")
            start_time = time.time()
            assets = analyse_content(get_fab_search_data(search, driver=chrome_driver, locale="fr"), search, check_name=True)
            for key, url in assets.items():
                print(f" - {key} : {url}")
            print(f'Time taken: {time.time() - start_time:.2f}')

    if test == 3:
        print(f"****\nTESTING get_fab_search_data() for an asset list  with selenium")
        print("Result (2025-07-03): Only the 1st search works, the followings will not return any results because of the appearance of a Captcha !!!")
        chrome_driver = chrome_driver_setup()
        for search in keywords:
            print(f"\nAsset list when searching '{search}':")
            start_time = time.time()
            assets = analyse_content(get_fab_search_data(search, driver=chrome_driver, locale="fr"), search, limit=10)
            for key, url in assets.items():
                print(f" - {key} : {url}")
            print(f'Time taken: {time.time() - start_time:.2f}')

    if test == 4:
        print(f"****\nTESTING get_fab_search_data() for an asset list with selenium with cleaning data between searches")
        print("Result (2025-07-03): Only the 1st search works, the followings will not return any results because of the appearance of a Captcha !!!")
        chrome_driver = chrome_driver_setup()
        for search in keywords:
            print(f"\nAsset list when searching '{search}':")
            start_time = time.time()
            assets = analyse_content(get_fab_search_data(search, driver=chrome_driver, locale="fr"), search, limit=10)
            for key, url in assets.items():
                print(f" - {key} : {url}")
            print(f'Time taken: {time.time() - start_time:.2f}')
            # Reset session data
            reset_session_data(chrome_driver)
            # change_user_agent
            change_user_agent(chrome_driver, get_random_user_agent())

    if test == 5:
        print(f"****\nTESTING get_fab_search_data() for an asset list with selenium with closing session between searches")
        print("Result (2025-07-03): OK ! All the successives searches work, each search took between 7 and 9 seconds to run")
        for search in keywords:
            print(f"\nAsset list when searching '{search}':")
            start_time = time.time()
            chrome_driver = chrome_driver_setup() # Create a new driver for each search
            assets = analyse_content(get_fab_search_data(search, driver=chrome_driver, locale="fr"), search, limit=10)
            for key, url in assets.items():
                print(f" - {key} : {url}")
            chrome_driver.quit()  # Close the driver after each search
            print(f'Time taken: {time.time() - start_time:.2f}')
