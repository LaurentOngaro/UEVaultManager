# coding: utf-8
"""
Implementation for:
- EPCAPI : Epic Games Client API
- GrabResult : Enum for the result of grabbing a page.
- create_empty_assets_extra : Create an empty asset extra dict.
- is_asset_obsolete : Check if an asset is obsolete.
"""
import json
import logging
import re
from enum import Enum

import requests
import requests.adapters
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

from UEVaultManager.models.exceptions import InvalidCredentialsError
from UEVaultManager.utils.cli import create_list_from_string


class GrabResult(Enum):
    """
    Enum for the result of grabbing a page.
    """
    NO_ERROR = 0
    # next codes could occur only with beautifulsoup data grabbing (UEVM Version 1.X.X.X)
    INCONSISTANT_DATA = 1
    PAGE_NOT_FOUND = 2
    CONTENT_NOT_FOUND = 3
    TIMEOUT = 4
    # next codes could occur only with API scraping only (UEVM version 2.X.X.X)
    PARTIAL = 5  # when asset has been added when owned asset data only (less complete that "standard" asset data)
    NO_APPID = 6  # no appid found in the data (will produce a file name like '_no_appId_asset_1e10acc0cca34d5c8ff7f0ab57e7f89f
    NO_RESPONSE = 7  # the url does not return HTTP 200


def is_asset_obsolete(supported_versions='', engine_version_for_obsolete_assets=None) -> bool:
    """
    :param supported_versions: the supported versions the check the obsolete status against.
    :param engine_version_for_obsolete_assets: the engine version to use to check if an asset is obsolete.
    :return: True if the asset is obsolete, False otherwise.
    """
    if not engine_version_for_obsolete_assets or not supported_versions:
        obsolete = False
    else:
        supported_versions_list = supported_versions.lower().replace('ue_', '')
        supported_versions_list = create_list_from_string(supported_versions_list)
        obsolete = True
        for _, version in enumerate(supported_versions_list):
            if version == '':
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
    :return: the empty asset extra dict.
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
        'supported_versions': '',
        'installed_folders': [],
        'grab_result': GrabResult.NO_ERROR.name,
    }


class EPCAPI:
    """
    Epic Games Client API.
    :param lc: the language code.
    :param cc: the country code.
    :param timeout: timeout for the request. Could be a float or a tuple of float (connect timeout, read timeout).
    """
    ignored_logger = None

    _user_agent = 'UELauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit'
    _store_user_agent = 'EpicGamesLauncher/14.0.8-22004686+++Portal+Release-Live'
    # required for the oauth request
    _user_basic = '34a02cf8f4414e29b15921876da36f9a'
    _pw_basic = 'daafbccc737745039dffe53d94fc76cf'
    _label = 'Live-EternalKnight'

    _oauth_host = 'account-public-service-prod03.ol.epicgames.com'
    _launcher_host = 'launcher-public-service-prod06.ol.epicgames.com'
    _entitlements_host = 'entitlement-public-service-prod08.ol.epicgames.com'
    _catalog_host = 'catalog-public-service-prod06.ol.epicgames.com'
    _ecommerce_host = 'ecommerceintegration-public-service-ecomprod02.ol.epicgames.com'
    _datastorage_host = 'datastorage-public-service-liveegs.live.use1a.on.epicgames.com'
    _library_host = 'library-service.live.use1a.on.epicgames.com'
    # Using the actual store host with a user-agent newer than 14.0.8 leads to a CF verification page,
    # but the dedicated graphql host works fine.
    # _store_gql_host = 'launcher.store.epicgames.com'
    _store_gql_host = 'graphql.epicgames.com'
    _artifact_service_host = 'artifact-public-service-prod.beee.live.use1a.on.epicgames.com'
    _login_url = 'www.unrealengine.com/id/login/epic'

    _url_marketplace = 'www.unrealengine.com/marketplace'
    _search_url = _url_marketplace + '/en-US'
    # _url_asset_list = 'https://www.unrealengine.com/marketplace/api/assets'
    _url_asset_list = _url_marketplace + '/api/assets'
    # _url_owned_assets = 'https://www.unrealengine.com/marketplace/api/assets/vault'
    _url_owned_assets = _url_asset_list + '/vault'
    # _url_asset = 'https://www.unrealengine.com/marketplace/api/assets/asset'
    _url_asset = _url_asset_list + '/asset'

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
        self.log = logging.getLogger('EPCAPI')
        self.notfound_logger = None  # will be setup when created in core.py
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

    def _extract_price_from_elt(self, dom_elt=None, asset_name='NO NAME') -> float:
        """
        Extracts the price from a BeautifulSoup element.
        :param dom_elt: the BeautifulSoup element.
        :param asset_name: the name of the asset (for display purpose only).
        :return: the price.
        """
        if dom_elt is None or dom_elt == '':
            self.log.debug(f'Price not found for {asset_name}')
            return 0.0
        price = 0.0
        try:
            # asset base price when logged
            price = dom_elt.text.strip('$')
            price = price.strip('€')
            price = float(price)
        except Exception as error:
            self.log.warning(f'Can not find the price for {asset_name}:{error!r}')
        return price

    def get_scrap_url(self, start=0, count=1, sort_by='effectiveDate', sort_order='DESC') -> str:
        """
        Return the scraping URL for an asset.
        """
        url = f'https://{self._url_asset_list}?start={start}&count={count}&sortBy={sort_by}&sortDir={sort_order}'
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
        # 'https://www.unrealengine.com/marketplace/api/assets/vault?start=1000&count=100'
        url = f'https://{self._url_owned_assets}?start={start}&count={count}'
        return url

    def get_marketplace_product_url(self, asset_slug: str = '') -> str:
        """
        Return the url for the asset in the marketplace.
        :param asset_slug: the asset slug.
        :return: the url.
        """
        url = f'https://{self._url_marketplace}/en-US/product/{asset_slug}'
        return url

    def get_api_product_url(self, uid: str = '') -> str:
        """
        Return the url for the asset using the UE API.
        :param uid: the id of the asset (not the slug, nor the catalog_id).
        :return: the url.
        """
        url = f'https://{self._url_asset}/{uid}'
        return url

    def get_scraped_asset_count(self, owned_assets_only=False) -> int:
        """
        Return the number of assets in the marketplace.
        :param owned_assets_only: whether to only the owned assets are counted.
        """
        assets_count = 0
        if owned_assets_only:
            url = f'https://{self._url_owned_assets}'
        else:
            url = f'https://{self._url_asset_list}'
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        json_content = r.json()
        try:
            assets_count = json_content['data']['paging']['total']
        except Exception as error:
            self.log.warning(f'Can not get the asset count from {url}:{error!r}')
        return assets_count

    def is_valid_url(self, url='') -> bool:
        """
        Check is the url is valid (i.e. http response status is 200).
        :param url: the url to check.
        :return: True if the url is valid.
        """
        result = False
        if not url:
            return result
        try:
            r = self.session.get(url, timeout=self.timeout)
        except (requests.exceptions.Timeout, ConnectionError):
            self.log.warning(f'Timeout for {url}')
            return result
        if r.status_code == 200:
            result = True
        return result

    def get_json_data_from_url(self, url='') -> dict:
        """
        Return the scraped assets.
        :param url: the url to scrap.
        :return: the json data.
        """
        json_data = {}
        if not url:
            return json_data
        r = self.session.get(url, timeout=self.timeout)
        # r.raise_for_status() # commented line because we want the exceptions to be raised
        json_data = r.json()
        return json_data

    def resume_session(self, session: dict) -> dict:
        """
        Resumes a session.
        :param session: the session.
        :return: the session.
        """
        self.session.headers['Authorization'] = f'bearer {session["access_token"]}'
        url = f'https://{self._oauth_host}/account/api/oauth/verify'
        r = self.session.get(url, timeout=self.timeout)
        if r.status_code >= 500:
            r.raise_for_status()

        j = r.json()
        if 'errorMessage' in j:
            self.log.warning(f'Login to EGS API failed with errorCode: {j["errorCode"]}')
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
        :return: the session.
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

        url = f'https://{self._oauth_host}/account/api/oauth/token'
        r = self.session.post(url, data=params, auth=self._oauth_basic, timeout=self.timeout)
        # Only raise HTTP exceptions on server errors
        if r.status_code >= 500:
            r.raise_for_status()

        j = r.json()
        if 'errorCode' in j:
            if j['errorCode'] == 'errors.com.epicgames.oauth.corrective_action_required':
                self.log.error(f'{j["errorMessage"]} ({j["correctiveAction"]}), '
                               f'open the following URL to take action: {j["continuationUrl"]}')
            else:
                self.log.error(f'Login to EGS API failed with errorCode: {j["errorCode"]}')
            raise InvalidCredentialsError(j['errorCode'])
        elif r.status_code >= 400:
            self.log.error(f'EGS API responded with status {r.status_code} but no error in response: {j}')
            raise InvalidCredentialsError('Unknown error')

        self.session.headers['Authorization'] = f'bearer {j["access_token"]}'
        # only set user info when using non-anonymous login
        if not client_credentials:
            self.user = j

        return j

    def get_item_token(self) -> str:
        """
        Get the item token.
        Unused but kept for the global API reference.
        :return: the item token using json format.
        """
        url = f'https://{self._oauth_host}/account/api/oauth/exchange'
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_item_assets(self, platform='Windows', label='Live'):
        """
        Get the item assets.
        :param platform: platform to get assets for.
        :param label: label of the assets.
        :return: the item assets using json format.
        """
        url = f'https://{self._launcher_host}/launcher/api/public/assets/{platform}'
        r = self.session.get(url, params=dict(label=label), timeout=self.timeout)
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
        :return: the item manifest using json format.
        """
        url = f'https://{self._launcher_host}/launcher/api/public/assets/v2/platform/{platform}/namespace/{namespace}/catalogItem/{catalog_item_id}/app/{app_name}/label/{label}'
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

    def get_library_items(self, include_metadata=True) -> list:
        """
        Get the library items.
        :param include_metadata: whether to include metadata.
        :return: the library items.
        """
        records = []
        url = f'https://{self._library_host}/library/api/public/items'
        r = self.session.get(url, params=dict(includeMetadata=include_metadata), timeout=self.timeout)
        r.raise_for_status()
        j = r.json()
        records.extend(j['records'])

        # Fetch remaining library entries as long as there is a cursor
        url = f'https://{self._library_host}/library/api/public/items'
        while cursor := j['responseMetadata'].get('nextCursor', None):
            r = self.session.get(url, params=dict(includeMetadata=include_metadata, cursor=cursor), timeout=self.timeout)
            r.raise_for_status()
            j = r.json()
            records.extend(j['records'])

        return records

    def search_for_asset_url(self, asset_name: str) -> []:
        """
        Find the asset url from the asset name by searching the asset name in the unreal engine marketplace.
        :param asset_name: asset name to search.
        :return: (The asset url, the asset name (converted or found), the grab result code).
        """
        # remove the suffix _EngineVersion (ex _4.27) at the end of the name to have a valid search value
        regex = r"_[4|5]\.\d{1,2}$"
        converted_name = re.sub(regex, '', asset_name, 0)
        # Replace ' ' by '%20'
        converted_name = converted_name.replace(' ', '%20')
        # SnakeCase
        # converted_name = inflection.underscore(converted_name)
        # Lower case
        converted_name_lower = converted_name.lower()
        # Replace '_' by '-'
        # converted_name_lower = converted_name_lower.replace('_', '-')

        # remove some not alphanumeric cars (NOT ALL, keep %)
        entry_list = [':', ',', '.', ';', '=', '?', '!', '#', "/", "$", "€"]
        for entry in entry_list:
            converted_name_lower = converted_name_lower.replace(entry, '')

        url = ''
        asset_slug = converted_name_lower
        # TODO: improve the following code to use the marketplace API instead of the website using beautifulsoup
        search_url_root = f'https://{self._search_url}/assets?keywords='
        search_url_full = search_url_root + converted_name_lower
        try:
            r = self.session.get(search_url_full, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.log.warning(f'Timeout for {asset_name}')
            return [url, asset_slug, GrabResult.TIMEOUT.name]
        if not r.ok:
            self.log.warning(f'Can not find the url for {asset_name}:{r.reason}')
            return [url, asset_slug, GrabResult.PAGE_NOT_FOUND.name]

        soup = BeautifulSoup(r.content, 'html.parser')
        links = []
        group_elt = soup.find('div', attrs={'class': 'asset-list-group'})

        if "No content found" in group_elt.getText():
            self.log.info(f'{asset_name} has not been not found in marketplace.It has been added to the notfound_logger file')
            if self.notfound_logger:
                self.notfound_logger.info(asset_name)
            return [url, asset_slug, GrabResult.CONTENT_NOT_FOUND.name]

        # find all links to assets that correspond to the search
        for link in group_elt.findAll('a', attrs={'class': 'mock-ellipsis-item mock-ellipsis-item-helper ellipsis-text'}):
            links.append(link.get('href'))

        # return the first one (probably the best choice)
        asset_slug = links[0].replace('/marketplace/en-US/product/', '')
        url = 'https://www.unrealengine.com' + links[0]
        return [url, asset_slug, GrabResult.NO_ERROR.name]

    def grab_assets_extra(self, asset_name: str, asset_title: str, verbose_mode=False, installed_asset=None) -> dict:
        """
        Grab the extra data of an asset (price, review...) using BeautifulSoup from the marketplace.
        :param asset_name: name of the asset.
        :param asset_title: title of the asset.
        :param verbose_mode: verbose mode.
        :param installed_asset: installed asset of the same name if any.
        :return: a dict with the extra data.
        """
        not_found_price = 0.0
        not_found_review = 0.0
        supported_versions = ''
        page_title = ''
        no_result = create_empty_assets_extra(asset_name=asset_name)

        # try to find the url of the asset by doing a search in the marketplace
        asset_url, asset_slug, error_code = self.search_for_asset_url(asset_title)

        # TODO: improve the following code to use the marketplace API instead of Scraping using beautifulsoup
        if asset_url == '' or error_code != GrabResult.NO_ERROR.name:
            self.log.info('No result found for grabbing data.\nThe asset name that has been searched for has been stored in the "Page title" Field')
            no_result['grab_result'] = error_code
            no_result['page_title'] = asset_slug
            return no_result
        try:
            response = self.session.get(asset_url)  # when using session, we are already logged in Epic game
            response.raise_for_status()
            self.log.info(f'Grabbing extra data for {asset_name}')
        except requests.exceptions.RequestException as error:
            self.log.warning(f'Can not get extra data for {asset_name}:{error!r}')
            self.log.info('No result found for grabbing data.\nThe asset name that has been searched for has been stored in the "Page title" Field')
            no_result['grab_result'] = error_code
            no_result['page_title'] = asset_slug
            return no_result

        soup_logged = BeautifulSoup(response.text, 'html.parser')
        price = not_found_price
        discount_price = not_found_price
        search_for_price = True
        # owned = False
        owned = True  # all the assets get with the legendary method are owned. No need to check. Could create incoherent info if parsing fails
        owned_elt = soup_logged.find('div', class_='purchase')
        if owned_elt is not None:
            if 'Free' in owned_elt.getText():
                # free price when logged
                price = 0.0
                search_for_price = False
                if verbose_mode:
                    self.log.info(f'{asset_name} is free (check 1)')
            elif 'Open in Launcher' in owned_elt.getText():
                # owned asset
                # owned = True
                # if verbose_mode:
                #     self.log.info(f'{asset_name} is already owned')

                # grab the price on a non logged soup (price will be available on that page only)
                try:
                    response = requests.get(asset_url, timeout=self.timeout)  # not using session, so not logged in Epic game
                    response.raise_for_status()
                    soup_not_logged = BeautifulSoup(response.text, 'html.parser')
                    owned_elt = soup_not_logged.find('div', class_='purchase')
                except requests.exceptions.RequestException:
                    pass

        if search_for_price and owned_elt is not None:
            if 'Sign in to Download' in owned_elt.getText():
                # free price when logged or not
                price = 0.0
                if verbose_mode:
                    self.log.info(f'{asset_name} is free (check 2)')
            else:
                # get price using the logged or the not logged soup
                # Note:
                #   when not discounted
                #       base-price is not available
                #       price is 'save-discount'
                #       discount-price is 0.0
                #   when discounted
                #       price is 'base-price'
                #       discount-price is 'save-discount'
                elt = owned_elt.find('span', class_='save-discount')
                current_price = self._extract_price_from_elt(elt, asset_name)
                elt = owned_elt.find('span', class_='base-price')
                base_price = self._extract_price_from_elt(elt, asset_name)
                if elt is not None:
                    # discounted
                    price = base_price
                    discount_price = current_price
                else:
                    # not discounted
                    price = current_price
                    discount_price = current_price

        # get review
        reviews_elt = soup_logged.find('div', class_='asset-detail-rating')
        if reviews_elt is not None:
            reviews_elt = reviews_elt.find('div', class_='rating-board__pop__title')
        if reviews_elt is not None:
            try:
                inner_span_elt = reviews_elt.find('span')
                content = inner_span_elt.text
                pos = content.index(' out of ')
                review = float(content[0:pos])
            except Exception as error:
                self.log.warning(f'Can not find the review for {asset_name}:{error!r}')
                review = not_found_review
        else:
            self.log.debug(f'reviews not found for {asset_name}')
            review = not_found_review

        # get Supported Engine Versions
        title_elt = soup_logged.find('span', class_='ue-version')
        if title_elt is not None:
            try:
                supported_versions = title_elt.text
            except Exception as error:
                self.log.warning(f'Can not find the Supported Engine Versions for {asset_name}:{error!r}')
        else:
            self.log.debug(f'Can not find the Supported Engine Versions for {asset_name}')
            review = not_found_review

        # get page title
        title_elt = soup_logged.find('h1', class_='post-title')
        if title_elt is not None:
            try:
                page_title = title_elt.text
            except Exception as error:
                self.log.warning(f'Can not find the Page title for {asset_name}:{error!r}')
        else:
            self.log.debug(f'Can not find the Page title not found for {asset_name}')
            review = not_found_review
        discount_percentage = 0.0 if (discount_price == 0.0 or price == 0.0 or discount_price == price) else int(
            (price - discount_price) / price * 100.0
        )
        discounted = (discount_price < price) or discount_percentage > 0.0

        # get Installed_Folders
        installed_folders = installed_asset.installed_folders if installed_asset else []
        self.log.info(f'GRAB results: asset_slug={asset_slug} discounted={discounted} owned={owned} price={price} review={review}')
        return {
            'asset_name': asset_name,
            'asset_slug': asset_slug,
            'price': price,
            'discount_price': discount_price,
            'review': review,
            'owned': owned,
            'discount_percentage': discount_percentage,
            'discounted': discounted,
            'asset_url': asset_url,
            'page_title': page_title,
            'supported_versions': supported_versions,
            'installed_folders': installed_folders,
            'grab_result': error_code,
        }

    def get_asset_data_from_marketplace(self, url: str) -> dict:
        """
        Get the asset data from the marketplace using beautifulsoup.
        :param url: the url to grab.

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
        try:
            response = self.session.get(url)  # when using session, we are already logged in Epic game
            response.raise_for_status()
            self.log.info(f'Grabbing asset data from {url}')
        except requests.exceptions.RequestException as error:
            self.log.warning(f'Can not get asset data for {url}:{error!r}')
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
            # exemple of json_dict
            # {
            #     "@context"   : "https://schema.org",
            #     "@type"      : "Product",
            #     "sku"        : "d27cf128fdc24e328cf950b019563bc5",
            #     "productID"  : "d27cf128fdc24e328cf950b019563bc5",
            #     "name"       : "Volcrate",
            #     "category"   : "Characters",
            #     "image"      : [
            #         "https://cdn1.epicgames.com/ue/item/Volcrate_FeaturedNew-894x488-ad93ea4be7589802d9dc289a4af3a751.png"
            #     ],
            #     "description": "Here is a Volcrate, this race is a crossing between a bird and a human. They mostly behave as barbarians with their impressive musculature, performing powerful devastating attacks.",
            #     "releaseDate": "2016-12-21T00:00:00.000Z",
            #     "brand"      : {
            #         "@type": "Brand",
            #         "name" : "Unreal Engine",
            #         "logo" : {
            #             "@type": "ImageObject",
            #             "url"  : "https://cdn2.unrealengine.com/Unreal+Engine%2Flogos%2FUnreal_Engine_Black-1125x1280-cfa228c80703d4ffbd1cc05eabd5ed380818da45.png"
            #         }
            #     },
            #     "offers"     : {
            #         "@type"        : "Offer",
            #         "price"        : "€32.01",
            #         "availability" : "http://schema.org/InStock",
            #         "priceCurrency": "EUR",
            #         "url"          : "https://www.unrealengine.com/marketplace/en-US/product/volcrate"
            #     }
            # }

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
                    self.log.warning(f"A key is missing in Script {index + 1}: {error!r}")
                    json_data['grab_result'] = GrabResult.PARTIAL.name
                    continue
        if json_data['url'].lower().replace('www.', '') != url.lower().replace('www.', ''):
            self.log.warning(f"URLs do not match: {json_data['url']} != {url}")
            json_data['grab_result'] = GrabResult.INCONSISTANT_DATA.name
        return json_data
