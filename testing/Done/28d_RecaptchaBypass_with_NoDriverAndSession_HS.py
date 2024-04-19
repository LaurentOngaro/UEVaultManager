# coding=utf-8
"""
TESTED: This script DOES NOT work as expected.
The user is never logged with the tests made
"""

from pathlib import Path

# install official package by running the following command in the terminal
# pip install undetected-chromedriver
# install my personal fork by running the following command in the terminal
# my fork fix option to resize the windows and an error at the end of the execution
# pip install -e git+https://github.com/LaurentOngaro/F_undetected-chromedriver#egg=undetected-chromedriver

import nodriver as uc
import time
import json

from requests.auth import HTTPBasicAuth
from nodriver import cdp
from nodriver.cdp.network import CookieParam, Headers, set_cookies, set_extra_http_headers

# not owned asset
url = "https://www.unrealengine.com/marketplace/en-US/product/ninja-combat"
asset_name = 'Ninja Combat'

# owned asset
url = 'https://www.unrealengine.com/marketplace/en-US/item/9ab5a1060b8345ddbf1adb09529dadca'
asset_name = 'Watermills / Nature Environment'

# text to check if login succeded
logged_text = 'Write a Review'

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
    '--no-first-run', '--no-default-browser-check', '--no-experiments', '--mute-audio', '--enable-gpu', '--disable-extensions',
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


async def uc_get_content(url, params):
    browser = await uc.start(**params)

    _user_basic = '34a02cf8f4414e29b15921876da36f9a'
    _pw_basic = 'daafbccc737745039dffe53d94fc76cf'
    _oauth_host = 'https://account-public-service-prod03.ol.epicgames.com'
    _oauth_basic = HTTPBasicAuth(_user_basic, _pw_basic)
    timeout = (7, 7)
    auth_url = f'{_oauth_host}/account/api/oauth/token'

    # read the files in
    auth_folder = Path('../.private/auth_data')  # TODO: add the path to settings ?

    # COOKIES
    cookies = Path(f'{auth_folder}/session_cookies.json').read_text() if Path(f'{auth_folder}/session_cookies.json').exists() else None
    cookies = json.loads(cookies) if cookies else {}
    # HEADERS:
    headers = Path(f'{auth_folder}/session_headers.json').read_text() if Path(f'{auth_folder}/session_headers.json').exists() else None
    headers = json.loads(headers) if headers else {}
    # Tokens
    refresh_token = Path(f'{auth_folder}/refresh_token.token').read_text() if Path(f'{auth_folder}/refresh_token.token').exists() else ''
    exchange_token = Path(f'{auth_folder}/exchange_code.token').read_text() if Path(f'{auth_folder}/exchange_code.token').exists() else ''
    authorization_code = Path(f'{auth_folder}/authorization_code.token').read_text() if Path(f'{auth_folder}/authorization_code.token'
                                                                                            ).exists() else ''

    # authorization_code
    if authorization_code:
        auth_params = dict(grant_type='authorization_code', code=authorization_code, token_type='eg1')
    # exchange_token
    if exchange_token:
        auth_params = dict(grant_type='exchange_code', exchange_code=exchange_token, token_type='eg1')
    # refresh_token:
    if refresh_token:
        auth_params = dict(grant_type='refresh_token', refresh_token=refresh_token, token_type='eg1')

    # test HS: send POST data to authentificate
    # see: self.request("POST", url, data=auth_params, auth=_oauth_basic, timeout=timeout)
    # error : TypeError: Object of type HTTPBasicAuth is not JSON serializable
    """
    post_params = dict(grant_type='exchange_code', exchange_code=exchange_token, token_type='eg1', auth=_oauth_basic, timeout=timeout)
    data=json.dumps(post_params).encode("utf-8")
    page = await browser._http._request(endpoint=auth_url, method='POST', data=data)
    await page.activate()
    """

    # test HS: change full headers and add Authorization with token
    """
    exemple de session headers when logged
    {'User-Agent': 'UELauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive', 'Authorization': 'bearer eg1~eyJraWQiOiJnX19WS2pTU21xSjB4WmoxUllrTEdLUTdkbkhpTTlNTGhGVndLUHlTREI0IiwiYWxnIjoiUFMyNTYifQ.eyJhcHAiOiJsYXVuY2hlciIsInN1YiI6IjA0YjMwZWI2NWU0NTRiZDc4MGM3YTA2NTIyNjc1NjViIiwibXZlciI6ZmFsc2UsImNsaWQiOiIzNGEwMmNmOGY0NDE0ZTI5YjE1OTIxODc2ZGEzNmY5YSIsImRuIjoibGF1cmVudE8iLCJhbSI6ImF1dGhvcml6YXRpb25fY29kZSIsInAiOiJlTnFsV050dTR6WVEvUi9EQVpKc25Dd0krQ0VJTnUwQ2kyNnhhZEhIZ0NKSE1tR0taSGxKNG41OWg2U2t5RmN4OFpObGlaZTVuRGxuU0dNMUQ4d1RFeW9wR0RINXIxdGV6eTI4Q0hqdFAxZ3cybnJpcVczQUw2L21UTGR0VUlKUkw3UnlSQ2dQVmxHSjR5Z25EcndYcW9tcjdJeUR0MjRjWlV3SDVVbGM3WHB1NktZRk5WaHhlVk45dVlUcWRnRTNpNXVLMzMyOVpIZjA4blp4ZlgxN3Q3aGRWS1FTVXVJRy9TSWNhaHBrWEVpS3lsSzdLVjdJU0xyeG9nVkNwZnlFSGE4NExUc1FKN2hWZEZwNFFJTmVRR29EdGc4b0FXdTFYZDRlSDBnTkRuMkI3NnJXdU41YmF3eUcwVG1NR3BsTkdvSUprVFFvdHNLRnVINVZVbU1XcEhpQkV0TmNxRnJobHpkejlGeDRDVEVDVy9OMndFRXdtZEJvdStudFZMUUZaeWdEQW1pOVpXVzdLbXJjU3Z1TUVVTWRnZ01SY3pYSFFVNHJPb0JvZ01wMEVCYnpmbXozNjZaVDJJS25uSHBLZnR6Ly9jZkQ3OTkrUFQ4OS9YeisrZmlZbHJOZTFCU3RyWVJDV01WWEgwVVkwd2dSRnRGUE1CRHQ4dXBxamdGM3pBcVRYbmJyak45ZElKNExRaGl0MFphRHhmOE1vYUl0Y1N0cWdaUDBkdHEwMmdMOEdTeGJVUWN4OEZNcEcvSitWaGpTN0I2c1RPckFuZGVXTmtEY3hzVUk3YUYvR0YxUUJtZ2psYm9aSWxIWENDZGNVdHVHS3ZGZm9pRkNlU3RVTWE3SWVLNDdXUmwxa0RWU1UxZEJaNEJ4TnByZTdkSC83U24wUHZpVlc5NGRHWVpVODFrdTNHS3BYUTlIWllzanlwbVNZU2xGN0g4K0pva29FTmZBb2MybDArVTR2a0hZTEhaelB6dGJXQkp1emlnd2t6VjBxN1oyQXlvMW83SUQxNTdxU3JHR1U2TFJMOUlDRnpRV2x0bVdjMGNWci9RYkRtMUZxaWJjd1drbVVJQWRVS3o4NlpLNm5nZS9YYWJCbGZnK3krYUFBNFhDOER5OTBjMkpJR1gvMEJUYytrZUUzYXpFZ09zRG90aXRtSWdsQmdOOXdyVWRRK2w5THhXdmpXQnVQTCt2cFVqaDhjTWhDcCswYUR3cFlyTVR1cjRrcE5icllEN3FaWWE1RlF4QU5VSkJEMUYwdE5WeEp4dGtGR1FJa25wTDJYb1VYc3lPUVVxREVtS3RFS2pyWk5YMDRLMVdvcHhuUjVOaWpIdWk2OHU2TTdxSjNjWStHWlFMVVlnK0ovRmJmam1BdWRRTzljVXlJdlQrZTl3WDQ4RWg5bGZ2bU9rUkZxeDBKVldWSUkySmZoR3hiMm9TRUQ5YmJHZDNBdjhHd2RhalZ1QlUzUnhYcHRsK0E0NWRyZXNiMGRyU3dBZDRabUpPNytLRzI5UDZNcHNrUGhPa3JCRFVKOWtEZTBzNDJkRitWTXk4cGk0cTdLR2FRaktKUWtvYnhGZUNUUUVXT2tyMlFGdEhFSnV6RXM3ZkVvNmoxQThud3pnODRZYll1WHNWUDJONU9kcEVsOHBJZmlzS2d5Wm5abG1KQ09UTktSdUNpUURES290S2R3UlpsSE5jMFNWblBtRm50TkxDSzdXOE9NVjUrRVhmcGlTK1VRcGlGNXgvRWJTdEh0WWJuWGpQS2tTRzUyZWY2YVdMRDFMN0MyV2I5K1BRcExPM0I5V0pDSjc0ZGZPZFR3aVJLNHJueUhsODNCV1l6bXQ4QTg0UHRmQlo0V1NTaXZhaUFnVzFpSUVINnJBRzE2RHlGMkpxTGpoNVB0aG5wWU0zeWdmdXZVdlpodnF5RHFpSFlkNVRlMlRHcDN3NmNmOEl2M3BDUlhyU3lKN3dxTzE5MXpwK25YZmtMaFJHUUtWRDhiSExrSnoxUHNYb1JtMEZLRjZXaUFQYW4wNDlKSDA0UnlnNXVJTTlsS1FWeU1UcWtkK3hCZkdvSHVsV2FIOXNHbkRDOWZGOTBUbjNOMVdRVVFRTzM0TGtIcW1UdC9jem9jRXppUUliNzY0YW0wK0dJUzVZVW1MRFJ2dkw5c25yaUNMNVd3Q3kwcHhuMHQwUzA4a3BIWUIvczlqOHVJOTFtRGk2Q2tKeW9XcE4wbE9MaCtFYW5EOTBTRVZaMThIdjhNTzd5aG90NWZBV24wZU1yeW1lWnhFWEdFelZ3Rit4MGg1U3A3V1lsc0lzOERoeXVFblM4U1pwK3l5VnRTcmlFTEJTeVRqcnBXaERUR0dLVjhJOHJJQ3RrNDI0elE3aEY1OEdxQVQzSzEycnh2cllQcnYyRGRCT1BTQ1QrQnliOUJqYytKWWhYV3BraW9xeDFMWnJEbklZVDk2NUhEdEVKQnN4M0dwczRrNGYvcUhPNlJYekdDZGdMdjRIdGFHNDh3PT0iLCJpYWkiOiIwNGIzMGViNjVlNDU0YmQ3ODBjN2EwNjUyMjY3NTY1YiIsInNlYyI6MSwiYWNyIjoidXJuOmVwaWM6bG9hOmFhbDEiLCJjbHN2YyI6ImxhdW5jaGVyIiwidCI6InMiLCJhdXRoX3RpbWUiOjE3MTM0NTcwMzUsImljIjp0cnVlLCJleHAiOjE3MTM0ODU4MzUsImlhdCI6MTcxMzQ1NzAzNSwianRpIjoiYzBhNzRhMjJhYzFkNDZlYzhlMjdkOTZkMmNkYWRjNTAifQ.YoX_shk6LxXHkPJk2irjhWLn4oAcnjuY-DUDepQxLFJffksOPichDa-CxR9usw5ni7d_IuKZ6AtWZHyJtyd4rb5nqCB020TXkyC-xBa9jEavqxlBTILcs7dEyR78JdjuXu4HYWNYsVZukenRYCESMDpNfvj0HTZwlvdj1qnT1vGZew5zKxnMG_kVRdJ5XCEl_BM-oeK7-ERnWuh78DIRKPgubY_FtFj16Zr-S5XfC6s3AcvF_2jCpmrFXZ-G7ndPzd3asC-UNOdJZK4lgSKemaih75RpbuXwbaxy86j03k3s0CPd4-mGzL6AUm0tQhxi2WHmbSP5NOcPaKBnLQDV5H3GZ6v_Fao7q1lZBhKZurk_y_-4GiGYb0iQoGJC01xjkiA39cGPSxg-LdO0Dz1WP9-MS7AORIXBho8IJ42TUTC0iFQ0dGtPiRziOlEeLsiTynrtlCDOFWm3to3oTJrWSa-brHkrwLZ-EV90RdH3HIJwTiAkvWlIiNu_ZkVmlpWD4zjKHtyNlHuaemYFSc-vQCH2yD61YRRjr0ySQBw9ifX5JH_9CCvCDATAb2H2r6qfsaIlqFsJusXxqYm1tcHU_VB9o6hjWL4CCA2xEgnR9BlVIEq1JCclfLYUJAgxp0p44tE7VyE0hWrF7BKhixhM4bU0aIc11clIOl7klGyXg2Y'}
    set_extra_http_headers({
        'User-Agent': 'UELauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit',
        'Accept-Encoding': 'gzip, deflate',
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Authorization': f'bearer {access_token}'
    })
    """

    # test HS: just add one field to header to add Authorization with token
    """
    # error: AttributeError: 'HTTPApi' object has no attribute '_session'
    browser._http._session.headers['Authorization'] = f'Bearer {access_token}'
    """

    # test HS: just add one field to header to add Authorization with token
    """
    # no error but user is not logged
    set_extra_http_headers(Headers({'Authorization': f'bearer {refresh_token}'}))
    """

    # test HS: loading cookies saved from a previous session
    """
    # No error but cookies are saved when login in UEVM
    for cookie in cookies:
        cookiesParam = CookieParam()
        cookiesParam.from_json(cookie)
        set_cookies(cookiesParam)
    """

    page = await browser.get(url)
    await page.activate()
    # set the size of the window AFTER the page is loaded
    # await page.set_window_size(window_left, window_top, window_width, window_height)
    # await page.minimize()
    params["content"] = await page.get_content()
    await browser.sleep(10)

    # exemple of sending CDP command
    # see https://chromedevtools.github.io/devtools-protocol for more all the command
    # await page.send(cdp.page.navigate(url='https://youtube.com'))
    # await browser.sleep(10)


uc.loop().run_until_complete(uc_get_content(url, params))

page_content = params["content"]
# print(page_content)
# TODO: use beautifulsoup to parse the page content
# check if page_content contains the text 'Ninja Combat'
is_ok = asset_name in page_content
print(f'RESULT CAPTCHA BYPASSED: {is_ok}')

is_logged = logged_text in page_content
print(f'RESULT USER LOGGED IN: {is_logged}')
print(f'Time taken: {time.time() - start_time:.2f}')
