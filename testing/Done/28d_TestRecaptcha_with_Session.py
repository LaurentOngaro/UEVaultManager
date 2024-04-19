# coding=utf-8
"""
TESTED: This script works as expected.
TIME TO LOAD THE PAGE: 2,4 seconds
"""
from pathlib import Path


import time
import json

import requests
from requests.auth import HTTPBasicAuth

# not owned asset
asset_url = "https://www.unrealengine.com/marketplace/en-US/product/ninja-combat"
asset_name = 'Ninja Combat'

# owned asset
# url = 'https://www.unrealengine.com/marketplace/en-US/item/9ab5a1060b8345ddbf1adb09529dadca'
# asset_name = 'Watermills / Nature Environment'

# text to check if login succeded
logged_text = 'Write a Review'


class TestLogin:
    """
    Test the login to the Epic Games Store
    """
    window_width = 1024
    window_height = 768
    # note:  the window position could be OUTSIDE the viewable area and its works !!
    # window_left = -window_width
    # window_top = -window_height
    window_left = 0
    window_top = 0
    browser_path = r"C:\Program Files\Chromium\Application\chrome.exe"
    oauth_host = 'https://account-public-service-prod03.ol.epicgames.com'
    user_agent = 'UELauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit'
    cur_folder = Path(".").absolute()
    auth_folder = Path('../.private/auth_data').absolute()  # TODO: add the path to settings ?
    url_login = f'{oauth_host}/account/api/oauth/token'
    url_resume = f'{oauth_host}/account/api/oauth/verify'
    user_data_file = r'C:\Users\laure\.config\UEVaultManager\json\user_data.json'

    def __init__(self):
        self._user_basic = '34a02cf8f4414e29b15921876da36f9a'
        self._pw_basic = 'daafbccc737745039dffe53d94fc76cf'
        self._oauth_basic = HTTPBasicAuth(self._user_basic, self._pw_basic)
        self.timeout = (10, 10)
        self.auth_url = f'{self.oauth_host}/account/api/oauth/token'

        # not used in session
        # self.params = {"headless": False, "use_subprocess": True}
        # self.params["browser_executable_path"] = self.browser_path
        # self.params["user_multi_procs"] = True  # will speed up the process
        # self.params['browser_args'] = [
        #     f'--window-size={self.window_width},{self.window_height}',  # set the initial size of the window
        #     f'--window-position={self.window_left},{self.window_top}',  # set the initial position of the window
        #     '--window-name="UndetectedChrome"',  # set the name of the window
        #     '--no-first-run', '--no-default-browser-check', '--no-experiments', '--mute-audio', '--enable-gpu', '--disable-extensions',
        #     # next options have been tested and are OK
        #     #'--start-maximized', # debug only
        #     #'--incognito',
        #
        #     # next options have been tested and could create issue
        #     # '--no-sandbox',  # needed for linux
        #
        #     # next options have been tested and CAUSE AN ERROR
        #     #'--headless',
        #     #'--silent-launch',
        # ]

        self.access_token = ''
        self.refresh_token = ''
        self.exchange_token = ''
        self.authorization_code = ''
        self.cookies = {}
        self.headers = {}
        self.default_headers = {
            "User-Agent": self.user_agent,  #
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",  #
            "Connection": "keep-alive",  #
        }

        self.session = None
        self.userdata = {}
        self.load_saved_data()

    def load_saved_data(self) -> None:
        """
        Lo
        :return:
        """
        # userdata
        userdata = Path(self.user_data_file).read_text() if Path(self.user_data_file).exists() else None
        self.userdata = json.loads(userdata) if userdata else {}

        # Tokens
        if Path(f'{self.auth_folder}/refresh_token.token').exists():
            self.refresh_token = Path(f'{self.auth_folder}/refresh_token.token').read_text()
        else:
            self.refresh_token = self.userdata['refresh_token']
        if Path(f'{self.auth_folder}/access_token.token').exists():
            self.access_token = Path(f'{self.auth_folder}/access_token.token').read_text()
        else:
            self.access_token = self.userdata['access_token']
        if Path(f'{self.auth_folder}/exchange_code.token').exists():
            self.exchange_token = Path(f'{self.auth_folder}/exchange_code.token').read_text()
        if Path(f'{self.auth_folder}/authorization_code.token').exists():
            self.authorization_code = Path(f'{self.auth_folder}/authorization_code.token').read_text()

        # COOKIES
        cookies = Path(f'{self.auth_folder}/session_cookies.json').read_text() if Path(f'{self.auth_folder}/session_cookies.json').exists() else None
        self.cookies = json.loads(cookies) if cookies else {}
        # HEADERS:
        headers = Path(f'{self.auth_folder}/session_headers.json').read_text() if Path(f'{self.auth_folder}/session_headers.json').exists() else None
        self.headers = json.loads(headers) if headers else self.default_headers
        self.headers['Authorization'] = f'bearer {self.access_token}'

    def login(self) -> bool:
        """
        Login using existing session data.
        """
        self.session = requests.session()

        auth_params = None
        # authorization_code
        if self.authorization_code:
            auth_params = dict(grant_type='authorization_code', code=self.authorization_code, token_type='eg1')
        # exchange_token
        if self.exchange_token:
            auth_params = dict(grant_type='exchange_code', exchange_code=self.exchange_token, token_type='eg1')
        # refresh_token:
        if self.refresh_token:
            auth_params = dict(grant_type='refresh_token', refresh_token=self.refresh_token, token_type='eg1')

        if not auth_params:
            print('No token found, login required')
            return False
        self.session.headers = self.headers
        r = self.session.post(self.url_login, data=auth_params, auth=self._oauth_basic, timeout=self.timeout)
        # Only raise HTTP exceptions on server errors
        if r.status_code >= 500:
            r.raise_for_status()
        j = r.json()
        if 'errorCode' in j:
            if j['errorCode'] == 'errors.com.epicgames.oauth.corrective_action_required':
                print(f'{j["errorMessage"]} ({j["correctiveAction"]}), '
                      f'open the following URL to take action: {j["continuationUrl"]}')
            else:
                print(f'Login to EGS API failed with errorCode: {j["errorCode"]}')
            return False
        elif r.status_code >= 400:
            print(f'EGS API responded with status {r.status_code} but no error in response: {j}')
            return False

        self.session.headers['Authorization'] = f'bearer {j["access_token"]}'
        print(f'Logged in as {j["displayName"]}')
        return True

    def resume(self) -> bool:
        """
        Resume a session
        """
        if not self.access_token:
            print(f'There is no session to resume')
            return False

        self.session = requests.session()

        self.session.headers = self.headers
        r = self.session.get(self.url_resume, timeout=self.timeout)
        # Only raise HTTP exceptions on server errors
        if r.status_code >= 500:
            r.raise_for_status()
            return False
        j = r.json()
        if 'errorMessage' in j:
            print(f'Login to EGS API failed with errorCode: {j["errorCode"]}')
            return False
        return True

    def get_content(self, url: str = '') -> str:
        """
        Get the content of the page
        :param url: the url of the page
        :return: the content of the page
        """
        if not url:
            return ''

        content = ''
        # test HS: send POST data to authentificate
        # see: self.request("POST", url, data=auth_params, auth=_oauth_basic, timeout=timeout)
        # error : TypeError: Object of type HTTPBasicAuth is not JSON serializable

        # exemple of sending CDP command
        # see https://chromedevtools.github.io/devtools-protocol for more all the command
        # await page.send(cdp.page.navigate(url='https://youtube.com'))
        # await browser.sleep(10)
        r = self.session.get(url, timeout=self.timeout)
        if r.ok:
            content = r.text

        return content


test_login = TestLogin()
start_time: float = time.time()
print(f'Opening {asset_url}')

test_login.resume()
page_content = test_login.get_content(asset_url)

# print(page_content)
# TODO: use beautifulsoup to parse the page content
# check if page_content contains the text 'Ninja Combat'
is_ok = asset_name in page_content
print(f'RESULT:\n')
print(f' - Check for {asset_name}')
print(f' - CAPTCHA BYPASSED: {is_ok}')
is_logged = logged_text in page_content
print(f' - USER LOGGED IN: {is_logged}')

print(f'Time taken: {time.time() - start_time:.2f}')
