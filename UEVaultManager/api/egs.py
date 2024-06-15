# coding: utf-8
"""
Implementation for:
- EPCAPI : Epic Games Client API
- create_empty_assets_extra : Create an empty asset extra dict.
- is_asset_obsolete : Check if an asset is obsolete.
"""
import json
import logging
from pathlib import Path
from typing import cast

import nodriver as uc
import requests
import requests.adapters
from bs4 import BeautifulSoup
from requests import Response
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.utils import dict_from_cookiejar
from selenium.webdriver.remote.command import Command

from UEVaultManager.models.exceptions import InvalidCredentialsError
from UEVaultManager.models.UCRequest import UCRequest
from UEVaultManager.models.UCResponse import UCResponse
from UEVaultManager.tkgui.modules.types import GrabResult, UCRequestType
from UEVaultManager.utils.cli import create_list_from_string


def is_asset_obsolete(supported_versions='', engine_version_for_obsolete_assets=None) -> bool:
    """
    :param supported_versions: supported versions the check the obsolete status against.
    :param engine_version_for_obsolete_assets: engine version to use to check if an asset is obsolete.
    :return: True if the asset is obsolete, False otherwise.
    """
    if not engine_version_for_obsolete_assets or not supported_versions:
        obsolete = False
    else:
        supported_versions_list = supported_versions.lower().replace('ue_', '').replace('ea', '')
        supported_versions_list = create_list_from_string(supported_versions_list)
        obsolete = True
        for _, version in enumerate(supported_versions_list):
            if not version:
                continue
            else:
                if float(engine_version_for_obsolete_assets) <= float(version):
                    obsolete = False
                    break
    return obsolete


def create_empty_assets_extra(asset_name: str) -> dict:
    """
    Create an empty asset extra dict.
    :param asset_name:  The name of the asset.
    :return: empty asset extra dict.
     """
    return {
        'asset_name': asset_name,
        'asset_slug': '',
        'price': 0,
        'discount_price': 0,
        'review': 0,
        'owned': True,
        'discount_percentage': 0,
        'discounted': False,
        'asset_url': '',
        'page_title': '',
        # 'supported_versions': '',
        'installed_folders': [],
        'grab_result': GrabResult.NO_ERROR.name,
    }


class EPCAPI:
    """
    Epic Games Client API.
    :param lc: language code.
    :param cc: country code.
    :param timeout: timeout for the request. Could be a float or a tuple of float (connect timeout, read timeout).
    """
    notfound_logger = None
    scrap_asset_logger = None

    _user_agent = 'UELauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit'
    # _user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    # _store_user_agent = 'EpicGamesLauncher/14.0.8-22004686+++Portal+Release-Live'
    # required for the oauth request
    # _label = 'Live-EternalKnight'
    _user_basic = '34a02cf8f4414e29b15921876da36f9a'
    _pw_basic = 'daafbccc737745039dffe53d94fc76cf'

    _oauth_host = 'https://account-public-service-prod03.ol.epicgames.com'
    _launcher_host = 'https://launcher-public-service-prod06.ol.epicgames.com'
    # _entitlements_host = 'entitlement-public-service-prod08.ol.epicgames.com'
    _catalog_host = 'https://catalog-public-service-prod06.ol.epicgames.com'
    # _ecommerce_host = 'https://ecommerceintegration-public-service-ecomprod02.ol.epicgames.com'
    # _datastorage_host = 'https://datastorage-public-service-liveegs.live.use1a.on.epicgames.com'
    # _library_host = 'https://library-service.live.use1a.on.epicgames.com'
    # Using the actual store host with a user-agent newer than 14.0.8 leads to a CF verification page,
    # but the dedicated graphql host works fine.
    # _store_gql_host = 'https://launcher.store.epicgames.com'
    # _store_gql_host = 'https://graphql.epicgames.com'
    # _artifact_service_host = 'https://artifact-public-service-prod.beee.live.use1a.on.epicgames.com'
    # _login_url = 'https://www.unrealengine.com/id/login/epic'

    # THESE URLs COULD NOT BE CALL USING SESSION ANYMORE DU TO RECATCHA VALIDATION
    _url_marketplace = 'https://www.unrealengine.com/marketplace'
    _url_asset_list = f'{_url_marketplace}/api/assets'
    _url_owned_assets = f'{_url_asset_list}/vault'
    _url_asset = f'{_url_asset_list}/asset'
    _url_search_asset = f'{_url_marketplace}/en-US/product'

    # page d'un asset avec son urlSlug
    # _url_marketplace/en-US/product/{'urlSlug}
    # https://www.unrealengine.com/marketplace/en-US/product/volcrate
    #
    # detail json d'un asset avec son id (et non pas son asset_id ou son catalog_id)
    # UE_ASSET/{el['id']}")
    # https://www.unrealengine.com/marketplace/api/assets/asset/d27cf128fdc24e328cf950b019563bc5
    #
    # liste json des reviews d'un asset avec son id
    # https://www.unrealengine.com/marketplace/api/review/d27cf128fdc24e328cf950b019563bc5/reviews/list?start=0&count=10&sortBy=CREATEDAT&sortDir=DESC
    #
    # liste json des questions d'un asset avec son id
    # https://www.unrealengine.com/marketplace/api/review/d27cf128fdc24e328cf950b019563bc5/questions/list?start=0&count=10&sortBy=CREATEDAT&sortDir=DESC
    #
    # liste json des tags courants
    # https://www.unrealengine.com/marketplace/api/tags
    """ 
    le champ release_info contient l'ID des manifest à telecharger pour chaque version
    (voir app_id) 
    urls dans EAM
    - start_session
    https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token
    
    - resume_session
    https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/verify
    
    - invalidate_sesion
    https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/sessions/kill/{}", access_token);
    
    - account_details
    https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/{}
    
    - account_ids_details
    https://account-public-service-prod03.ol.epicgames.com/account/api/public/account
    
    - account_friends
    https://friends-public-service-prod06.ol.epicgames.com/friends/api/public/friends/{}?includePending={}", id, include_pending);
    
    # asset
    https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/public/assets/{}?label={}", plat, lab);
    
    - asset_manifest
    https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/public/assets/v2/platform/{}/namespace/{}/catalogItem/{}/app/{}/label/{}",
    
    - asset_info
    https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/namespace/{}/bulk/items?id={}&includeDLCDetails=true&includeMainGameDetails=true&country=us&locale=lc",asset.namespace, asset.catalog_item_id);
    
    - game_token
    https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange"
    
    - ownership_token
    https://ecommerceintegration-public-service-ecomprod02.ol.epicgames.com/ecommerceintegration/api/public/platforms/EPIC/identities/{}/ownershipToken",
    
    - user_entitlements
    https://entitlement-public-service-prod08.ol.epicgames.com/entitlement/api/account/{}/entitlements?start=0&count=5000",
    
    - library_items
    https://library-service.live.use1a.on.epicgames.com/library/api/public/items?includeMetadata={}", include_metadata)
    https://library-service.live.use1a.on.epicgames.com/library/api/public/items?includeMetadata={}&cursor={}", include_metadata, c)
    """

    def __init__(self, lc='en', cc='US', timeout=(7, 7)):
        self.logger = logging.getLogger('EPCAPI')
        self.session = requests.session()
        self.session.headers['User-Agent'] = self._user_agent
        # increase maximum pool size for multithreaded metadata requests
        self.session.mount('https://', requests.adapters.HTTPAdapter(pool_maxsize=16))

        self.unauth_session = requests.session()
        self.unauth_session.headers['User-Agent'] = self._user_agent

        self._oauth_basic = HTTPBasicAuth(self._user_basic, self._pw_basic)

        self.access_token = None
        self.user = None

        self.language_code = lc
        self.country_code = cc

        self.timeout = timeout
        self._uc_browser = None
        self._uc_request = UCRequest()
        self.debug_mode = False  # TODO: make it a setting or use the gui_g.settings.debug_mode (not imported here)
        # set to true to use "NoDriver" object instead of a usual session object to bypass captcha on marketplace pages
        self.bypass_captcha = False

    def extract_price(self, price_text=None, asset_name='Unknown') -> float:
        """
        Extracts the price from a string.
        :param price_text: string to extract the price from.
        :param asset_name: name of the asset (for display purpose only).
        :return: price.
        """
        if not price_text:
            self.logger.debug(f'Price not found for {asset_name}')
            return 0.0
        price = 0.0
        try:
            # asset base price when logged
            price = str(price_text)
            price = price.strip('$€')
            price = price.replace(',', '')
            price = float(price)
        except Exception as error:
            self.logger.warning(f'Can not find the price for {asset_name}:{error!r}')
        return price

    def get_scrap_url(self, start=0, count=1, sort_by='effectiveDate', sort_order='DESC') -> str:
        """
        Return the scraping URL for an asset.
        """
        url = f'{self._url_asset_list}?start={start}&count={count}&sortBy={sort_by}&sortDir={sort_order}'
        # other possible filters
        # to see the list of possible filters: https://www.unrealengine.com/marketplace/en-US/assets and use filters on the right panel.
        """
        # can add multiple platform filters
        # Windows, Android, Linux, Mac, PS4, Nintendo%20Switch, Win32, iOS, Xbox%20One, HTML5...
        url += f'&platform={platform}'

        # can add multiple compatibleWith filters
        url += f'&compatibleWith=UE_5.2'

        # can add multiple tag filters
        url += f'&tag=22'

        url += f'&discountPercentageRange={discount_percent}'
        url += f'&priceRange=%5B{prince_min*100}%2C{prince_max*100}'
        """
        return url

    def get_owned_scrap_url(self, start=0, count=1) -> str:
        """
        Return the scraping URL for an owned asset.
        """
        url = f'{self._url_owned_assets}?start={start}&count={count}'
        return url

    def get_marketplace_product_url(self, asset_slug: str = '') -> str:
        """
        Return the url for the asset in the marketplace.
        :param asset_slug: asset slug.
        :return: url.
        """
        url = f'{self._url_search_asset}/{asset_slug}'
        return url

    def get_api_product_url(self, uid: str = '') -> str:
        """
        Return the url for the asset using the UE API.
        :param uid: id of the asset (not the slug, nor the catalog_id).
        :return: url.
        """
        url = f'{self._url_asset}/{uid}'
        return url

    def get_owned_library(self) -> dict:
        """
        Get the owned library, INCLUDING the epic game assets owned
        :return: dict of assets.
        """
        platform = 'Windows'
        label = 'Live'
        json_data = {}
        try:
            r = self.session.get(f'{self._launcher_host}/launcher/api/public/assets/{platform}', params=dict(label=label), timeout=self.timeout)
            if r.ok:
                json_data = r.json()
        except Exception as error:
            self.logger.warning(f'Can not get the get owned library assets: {error!r}')
        return json_data

    def get_available_assets_count(self) -> int:
        """
        Return the number of assets in the marketplace.
        """
        url = self._url_asset_list
        r = self.get_url_with_uc(url, timeout=self.timeout, force_bypass_captcha=True)
        try:
            json_content = r.json()
            return int(json_content['data']['paging']['total'])
        except Exception as error:
            self.logger.warning(f'Can not get the asset count from {url}: {error!r}')
            return 0

    def is_valid_url(self, url='') -> bool:
        """
        Check is the url is valid (i.e. http response status is 200).
        :param url: url to check.
        :return: True if the url is valid.
        """
        if not url:
            return False

        try:
            r = self.get_url_with_uc(url, timeout=self.timeout)
        except (Exception, ):
            self.logger.warning(f'Timeout for {url}')
            raise ConnectionError()
        if r.status_code == 200:
            return True

    def get_json_data_from_url(self, url='', override_timeout=-1) -> dict:
        """
        Return the scraped assets.
        :param url: url to scrap.
        :param override_timeout: override the timeout set for the current object.
        :return: json data.

        Notes:
            Getting the data could take more time than other calls to the API. Use the override_timeout parameter to set a longer timeout if needed.
        """
        json_data = {}
        if not url:
            return json_data

        timeout = self.timeout if override_timeout == -1 else override_timeout
        r = self.get_url_with_uc(url, timeout=timeout)
        # print session content for debug
        # noinspection GrazieInspection
        # from pprint import pprint

        # try:
        #     session = self.session
        #     content = r.text
        #     print('\n\n===================\n\n')
        #     pprint(vars(session), depth=20, compact=True, width=120, sort_dicts=False)
        #     print('\n\n===================\n\n')
        #     print(url)
        #     print('\n\n===================\n\n')
        #     print(content)
        # except Exception as e:
        #     print(e)
        if r.status_code == 403:
            # probably a captcha page
            # make a second request to get the json data with captcha bypass
            self.logger.warning(f'403 Forbidden result for {url}. Testing a request with captcha bypass.')
            old_bypass_captcha = self.bypass_captcha
            self.bypass_captcha = True
            try:
                r = self.get_url_with_uc(url, timeout=timeout)
                if not r.ok:
                    self.logger.warning(f'Request with captcha bypass failed')
            except Exception as error:
                self.logger.warning(f'Request with captcha bypass failed. Error {error!r}')
                self.bypass_captcha = old_bypass_captcha

        return r.json() if r.ok else {}

    def resume_session(self, session: dict) -> dict:
        """
        Resumes a session.
        :param session: session to resume.
        :return: session.
        """
        self.session.headers['Authorization'] = f'bearer {session["access_token"]}'
        url = f'{self._oauth_host}/account/api/oauth/verify'
        r = self.session.get(url, timeout=self.timeout)
        if r.status_code >= 500:
            r.raise_for_status()

        j = r.json()
        if 'errorMessage' in j:
            self.logger.warning(f'Login to EGS API failed with errorCode: {j["errorCode"]}')
            raise InvalidCredentialsError(j['errorCode'])

        # update other data
        session.update(j)
        self.user = session
        return self.user

    def start_session(
        self, refresh_token: str = None, exchange_token: str = None, authorization_code: str = None, client_credentials: bool = False
    ) -> dict:
        """
        Start a session.
        :param refresh_token: refresh token.
        :param exchange_token: exchange token.
        :param authorization_code: authorization code.
        :param client_credentials: client credentials.
        :return: session.
        :raise: ValueError,InvalidCredentialsError.
        """
        if refresh_token:
            params = dict(grant_type='refresh_token', refresh_token=refresh_token, token_type='eg1')
        elif exchange_token:
            params = dict(grant_type='exchange_code', exchange_code=exchange_token, token_type='eg1')
        elif authorization_code:
            params = dict(grant_type='authorization_code', code=authorization_code, token_type='eg1')
        elif client_credentials:
            params = dict(grant_type='client_credentials', token_type='eg1')
        else:
            raise ValueError('At least one token type must be specified!')

        url = f'{self._oauth_host}/account/api/oauth/token'
        r = self.session.post(url, data=params, auth=self._oauth_basic, timeout=self.timeout)
        # Only raise HTTP exceptions on server errors
        if r.status_code >= 500:
            r.raise_for_status()

        j = r.json()
        if 'errorCode' in j:
            if j['errorCode'] == 'errors.com.epicgames.oauth.corrective_action_required':
                self.logger.error(
                    f'{j["errorMessage"]} ({j["correctiveAction"]}), '
                    f'open the following URL to take action: {j["continuationUrl"]}'
                )
            else:
                self.logger.error(f'Login to EGS API failed with errorCode: {j["errorCode"]}')
            raise InvalidCredentialsError(j['errorCode'])
        elif r.status_code >= 400:
            self.logger.error(f'EGS API responded with status {r.status_code} but no error in response: {j}')
            raise InvalidCredentialsError('Unknown error')

        self.session.headers['Authorization'] = f'bearer {j["access_token"]}'

        # only set user info when using non-anonymous login
        if not client_credentials:
            self.user = j

        if self.debug_mode:
            self.save_auth_data(refresh_token, exchange_token, authorization_code)

        return j

    def get_item_token(self) -> str:
        """
        Get the item token.
        Unused but kept for the global API reference.
        :return: item token using json format.
        """
        url = f'{self._oauth_host}/account/api/oauth/exchange'
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_item_manifest(self, namespace, catalog_item_id, app_name, platform='Windows', label='Live') -> dict:
        """
        Get the item manifest.
        :param namespace:  namespace.
        :param catalog_item_id: catalog item id.
        :param app_name: Asset name.
        :param platform: platform to get manifest for.
        :param label: label of the manifest.
        :return: item manifest using json format.
        """
        url = f'{self._launcher_host}/launcher/api/public/assets/v2/platform/{platform}/namespace/{namespace}/catalogItem/{catalog_item_id}/app/{app_name}/label/{label}'
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_item_info(self, namespace: str, catalog_item_id: str) -> (dict, int):
        """
        Get the item info.
        :param namespace: namespace of the item.
        :param catalog_item_id: catalog item id of the item.
        :return: (The item info, status code).
        """
        url = f'https://{self._catalog_host}/catalog/api/shared/namespace/{namespace}/bulk/items'
        r = self.session.get(
            url,
            params=dict(
                id=catalog_item_id, includeDLCDetails=True, includeMainGameDetails=True, country=self.country_code, locale=self.language_code
            ),
            timeout=self.timeout
        )
        r.raise_for_status()
        return r.json().get(catalog_item_id, None), r.status_code

    def get_asset_data_from_marketplace(self, url: str) -> dict:
        """
        Get the asset data from the marketplace using beautifulsoup.
        :param url: url to grab.

        Notes:
            This is the only way I know to get the id of an asset from its slug (or url)
        """
        empty_data = {
            'id': '',
            'name': '',
            'category': '',
            'description': '',
            'image': '',
            'release_date': '',
            'url': '',
            'price': '',
            'price_currency': '',
            'page_title': '',
            'grab_result': '',
        }
        json_data = empty_data.copy()
        asset_slug = url.split('/')[-1]
        json_data['page_title'] = asset_slug
        response = self.get_url_with_uc(url)
        if response.ok and response.content:
            self.logger.info(f'Grabbing asset data from {url}')
        else:
            self.logger.warning(f'Can not get asset data for {url}')
            json_data['grab_result'] = GrabResult.PAGE_NOT_FOUND.name
            return json_data

        json_data['grab_result'] = GrabResult.NO_ERROR.name

        soup = BeautifulSoup(response.content, 'html.parser')

        # Finding all script tags in the HTML
        # scripts = soup.find_all('script')
        # Finding all script tags with the type 'application/ld+json' in the HTML
        scripts = soup.find_all('script', {'type': 'application/ld+json'})

        for index, script in enumerate(scripts):
            # Remove script tags
            json_text = script.string

            # Convert to Python dictionary
            json_dict = json.loads(json_text)

            # check if the script describes a product
            if json_dict['@type'] == 'Product':
                try:
                    json_data['id'] = json_dict['productID']
                    json_data['name'] = json_dict['name']
                    json_data['category'] = json_dict['category']
                    json_data['description'] = json_dict['description']
                    json_data['image'] = json_dict['image']
                    json_data['release_date'] = json_dict['releaseDate']
                    json_data['url'] = json_dict['offers']['url']  # must be the same as url
                    json_data['price'] = json_dict['offers']['price']
                    json_data['price_currency'] = json_dict['offers']['priceCurrency']
                except KeyError as error:
                    self.logger.warning(f"A key is missing in Script {index + 1}: {error!r}")
                    json_data['grab_result'] = GrabResult.PARTIAL.name
                    continue
        if json_data['url'].lower().replace('www.', '') != url.lower().replace('www.', ''):
            self.logger.warning(f"URLs do not match: {json_data['url']} != {url}")
            json_data['grab_result'] = GrabResult.INCONSISTANT_DATA.name
        return json_data

    def save_auth_data(self, refresh_token: str = None, exchange_token: str = None, authorization_code: str = None) -> None:
        """
        Save user and authorization data into files. This is useful for debugging.
        :param refresh_token:
        :param exchange_token:
        :param authorization_code:
        """
        keep_existing = True  # True is usefull to keep the authorization_code created at first loggin
        auth_folder = Path('../.private/auth_data')  # TODO: add the path to settings ?
        # delete the content folder if it exists
        if auth_folder.exists():
            if not keep_existing:
                for file in auth_folder.iterdir():
                    file.unlink()
        else:
            auth_folder.mkdir(parents=True, exist_ok=True)
        # COOKIES: see: https://scrapfly.io/blog/save-and-load-cookies-in-requests-python/
        cookies = dict_from_cookiejar(self.session.cookies)
        if cookies:
            Path(f'{auth_folder}/session_cookies.json').write_text(json.dumps(cookies))
        # HEADERS:
        # NOTE! self.session.headers is a CaseInsensitiveDict object, not a dict
        headers = dict(self.session.headers)
        if headers:
            Path(f'{auth_folder}/session_headers.json').write_text(json.dumps(headers))
        # Tokens
        if refresh_token:
            Path(f'{auth_folder}/refresh_token.token').write_text(refresh_token)
        if exchange_token:
            Path(f'{auth_folder}/exchange_code.token').write_text(exchange_token)
        if authorization_code:
            Path(f'{auth_folder}/authorization_code.token').write_text(authorization_code)

    def get_url_with_uc(self, url: str, timeout=None, force_bypass_captcha: bool = False) -> Response:
        """
        Return the response of an url request:
        - using the Nodriver object if the url concerns the epic marketplace.
        - using the session object if not
        :param url: url to fix.
        :param timeout: timeout for the request.
        :param force_bypass_captcha: force the bypass of the captcha.
        :return: response Object.

        NOTES:
            When using Nodriver,
            The parameters for the browser and the request are stored in self._uc_request.params
            The response will be stored in self._uc_request.response.
        """
        if not timeout:
            timeout = self.timeout

        uc_response = UCResponse()
        uc_response.request = self.session.request
        # get the connection object from the current session
        # we use self._url_marketplace as default url for the connection
        adapter = cast(HTTPAdapter, self.session.get_adapter(self._url_marketplace))
        connection = adapter.get_connection(self._url_marketplace)
        uc_response.connection = connection
        self._uc_request.request_type = UCRequestType.NORMAL  # by default, we consider we are using a normal request
        self._uc_request.response = uc_response

        # method_for_get_session = 0 # use a "normal" session get. Will not bypass a captcha if present
        # method_for_get_session = 1 # nodriver
        # method_for_get_session = 2 # reqdriver

        if force_bypass_captcha or self.bypass_captcha or url.startswith(self._url_asset_list) or url.startswith(self._url_search_asset):
            method_for_get_session = 1
        else:
            method_for_get_session = 0  # simple session get

        # force a method
        # method_for_get_session = 0  # debug only

        if method_for_get_session == 1:
            # test nodriver
            # install by: pip install nodriver
            # RESULT:
            #   response is OK, BUT the user is not logged in

            del self.session.cookies['EPIC_CLIENT_SESSION']  # this data cause a http 400 error because its value is too big
            # noinspection GrazieInspection
            # has_captcha = response.content.find(b"Please complete a security check to continue") != -1
            if not self._uc_browser:
                self.init_uc_browser()
            uc.loop().run_until_complete(self.uc_get_content(url))
            # note that self._uc_request is updated by the uc_get_content method
            return self._uc_request.response
        elif method_for_get_session == 2:
            # test reqdriver
            # install by: pip install reqdriver

            # RESULT:
            #   HS: response is empty
            # noinspection PyUnresolvedReferences
            from reqdriver import RequestsDriver
            from selenium.webdriver.chrome.options import Options
            custom_options = Options()
            custom_options.add_argument('--headless')
            if not self._uc_browser:
                req_driver = RequestsDriver(self.session, custom_options=custom_options)
                self._uc_browser = req_driver.get_driver()
                result_dict: dict = self._uc_browser.execute(Command.GET, {"url": url})
                uc_response.content = result_dict['value']
                uc_response.status_code = 200 if uc_response.content else 403
                self._uc_request.response = uc_response
                self._uc_request.request_type = UCRequestType.USING_UD
                return uc_response
        else:
            # use a "normal" session get. Will not bypass the captcha if present
            return self.session.get(url, timeout=timeout)

    def init_uc_browser(self) -> None:
        """
        Initialize the undetected Chrome Browser.

        NOTES:
            The parameters for the browser and the request are stored in self._uc_request.params
            The response will be stored in self._uc_request.response.
        """
        window_width = 1024 if self.debug_mode else 100
        window_height = 768 if self.debug_mode else 100
        # note:  the window position could be displayed OUTSIDE the current screen, and it works !!
        window_left = -window_width if not self.debug_mode else 0
        window_top = -window_height if not self.debug_mode else 0

        params = {}
        browser_path = r'C:\Program Files\Chromium\Application\chrome.exe'  # TODO: add the default browser_path to the settings or add a new check to find the browser
        params['headless'] = False  # True will not bypass the captcha
        params['use_subprocess'] = True  # False will crash the script
        params['browser_executable_path'] = browser_path
        params['user_multi_procs'] = True  # will speed up the process

        # set some arguments for the browser
        # full list: https://peter.sh/experiments/chromium-command-line-switches/
        params['browser_args'] = [
            f'--window-size={window_width},{window_height}',  # set the initial size of the window
            f'--window-position={window_left},{window_top}',  # set the initial position of the window
            '--window-name="UndetectedChrome"',  # set the name of the window
            '--no-first-run', '--no-default-browser-check', '--no-experiments', '--mute-audio', '--enable-gpu', '--disable-extensions',
            # next options have been tested and are OK
            # '--start-maximized', # debug only
            # '--incognito',

            # next options have been tested and could create issue
            # '--no-sandbox',  # needed for linux

            # next options have been tested and CAUSE AN ERROR
            # '--headless',
            # '--silent-launch',
        ]
        self._uc_request.params = params

        response = self._uc_request.response
        response.request = self.session.request
        # get the connection object from the current session
        # we use self._url_marketplace as default url for the connection
        adapter = cast(HTTPAdapter, self.session.get_adapter(self._url_marketplace))
        connection = adapter.get_connection(self._url_marketplace)
        response.connection = connection
        self._uc_request.response = response
        uc_logger = logging.getLogger('nodriver.core.browser')
        uc_logger.setLevel(logging.WARNING)  # disable info level because too verbose

    async def uc_get_content(self, url) -> None:
        """
        Get the content of a page using the undetected Chrome driver.
        :param url: url to get the content from.

        NOTES:
            The response will be stored in self._uc_request.response.
        """
        self._uc_browser = await uc.start(**self._uc_request.params)
        page = await self._uc_browser.get(url)
        await page.activate()
        # add a delai to let the page load
        # await page.wait(1)
        raw_content = await page.get_content()
        await page.close()
        response = self._uc_request.response
        response.headers = self.session.headers
        response.raw = raw_content
        response.url = url
        response.status_code = 200 if raw_content else 403
        self._uc_request.request_type = UCRequestType.USING_UD
        self._uc_request.response = response
        if response.status_code == 403:
            return

        soup = BeautifulSoup(raw_content, 'html.parser')
        if soup:
            # check if the page contains a captcha
            captcha_tag = soup.find('div', class_='cf_challenge_container')
            if captcha_tag:
                response.status_code = 403
                return

            # get the charset value from the header of raw_content
            charset_tag = soup.find('meta', charset=True)
            response.encoding = charset_tag.get('charset', response.encoding) if charset_tag else 'utf-8'

            # if response contains json data, raw_content is a container where the real content is stored between <pre> and </pre>
            pre_tag = soup.find('pre')
            response.content = pre_tag.text if pre_tag else raw_content

            # convert content to bytes because it's needed for the json decoding in response.json()
            response.content = response.content.encode(response.encoding)
            response.status_code = 200
        self._uc_request.response = response

    def get_last_request_type(self) -> UCRequestType:
        """
        Return the type of the last request.
        """
        return self._uc_request.request_type
