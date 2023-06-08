# coding: utf-8
"""
Implementation for:
- EPCAPI : Epic Games Client API
- GrabResult : Enum for the result of grabbing a page.
- create_empty_assets_extras : Creates an empty asset extras dict.
"""
import logging
import re
import urllib.parse
from enum import Enum

import requests
import requests.adapters
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

from UEVaultManager.models.exceptions import InvalidCredentialsError


class GrabResult(Enum):
    """
    Enum for the result of grabbing a page.
    """
    NO_ERROR = 0
    INCONSISTANT_DATA = 1
    PAGE_NOT_FOUND = 2
    CONTENT_NOT_FOUND = 3
    TIMEOUT = 4


def create_empty_assets_extras(asset_name: str) -> dict:
    """
    Creates an empty asset extras dict.
    :param asset_name:  The name of the asset.
    :return: The empty asset extras dict.
     """
    return {
        'asset_name': asset_name,
        'asset_slug': '',
        'price': 0,
        'discount_price': 0,
        'review': 0,
        'owned': False,
        'discount_percentage': 0,
        'discounted': False,
        'asset_url': '',
        'page_title': '',
        'supported_versions': '',
        'grab_result': GrabResult.NO_ERROR.name,
    }


class EPCAPI:
    """
    Epic Games Client API
    :param lc: The language code.
    :param cc: The country code.
    :param timeout: The timeout for requests.
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
    # UE_MARKETPLACE/en-US/product/{jjd['urlSlug']}
    # https://www.unrealengine.com/marketplace/en-US/product/cloudy-dungeon
    #
    # detail json d'un asset avec son id (et non pas son asset_id ou son catalog_id)
    # UE_ASSET/{el['id']}")
    # https://www.unrealengine.com/marketplace/api/assets/asset/5cb2a394d0c04e73891762be4cbd7216
    #
    # liste json des reviews d'un asset avec son id
    # https://www.unrealengine.com/marketplace/api/review/4ede75b0f8424e37a92316e75bf64cae/reviews/list?start=0&count=10&sortBy=CREATEDAT&sortDir=DESC
    #
    # liste json des questions d'un asset avec son id
    # https://www.unrealengine.com/marketplace/api/review/5cb2a394d0c04e73891762be4cbd7216/questions/list?start=0&count=10&sortBy=CREATEDAT&sortDir=DESC

    def __init__(self, lc='en', cc='US', timeout=10.0):
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

        self.request_timeout = timeout if timeout > 0 else None

    def _extract_price_from_elt(self, dom_elt=None, asset_name='NO NAME') -> float:
        """
        Extracts the price from a BeautifulSoup element.
        :param dom_elt: The BeautifulSoup element.
        :param asset_name: The name of the asset (for display purpose only).
        :return: The price.
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

    def get_auth_url(self) -> str:
        """
        Returns the url for the oauth login.
        :return: The url
        """
        login_url = 'https://www.epicgames.com/id/login?redirectUrl='
        redirect_url = f'https://www.epicgames.com/id/api/redirect?clientId={self._user_basic}&responseType=code'
        return login_url + urllib.parse.quote(redirect_url)

    def get_scrap_url(self, start=0, count=1, sort_by='effectiveDate', sort_order='DESC') -> str:
        """
        Return the scraping URL
        """
        scrap_url = f'https://{self._url_asset_list}?start={start}&count={count}&sortBy={sort_by}&sortDir={sort_order}'
        return scrap_url

    def get_scrapped_asset_count(self) -> int:
        """
        Return the scraping URL
        """
        assets_count = 0
        url = f'https://{self._url_asset_list}'
        r = self.session.get(url, timeout=self.request_timeout)
        r.raise_for_status()
        json_content = r.json()
        try:
            assets_count = json_content['data']['paging']['total']
        except Exception as error:
            self.log.warning(f'Can not get the asset count from {url}:{error!r}')
        return assets_count

    def get_scrapped_assets(self, url='') -> dict:
        """
        Return the scraping URL
        """
        json_data = {}
        if not url:
            return json_data
        r = self.session.get(url, timeout=self.request_timeout)
        r.raise_for_status()
        json_data = r.json()
        return json_data

    def resume_session(self, session: dict) -> dict:
        """
        Resumes a session.
        :param session: The session.
        :return: The session.
        """
        self.session.headers['Authorization'] = f'bearer {session["access_token"]}'
        url = f'https://{self._oauth_host}/account/api/oauth/verify'
        r = self.session.get(url, timeout=self.request_timeout)
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
        Starts a session.
        :param refresh_token: refresh token
        :param exchange_token: exchange token
        :param authorization_code: authorization code
        :param client_credentials: client credentials
        :return: The session.
        :raise: ValueError,InvalidCredentialsError
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
        r = self.session.post(url, data=params, auth=self._oauth_basic, timeout=self.request_timeout)
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
        Gets the item token.
        Unused but kept for the global API reference.
        :return: The item token using json format
        """
        url = f'https://{self._oauth_host}/account/api/oauth/exchange'
        r = self.session.get(url, timeout=self.request_timeout)
        r.raise_for_status()
        return r.json()

    def get_ownership_token(self, namespace: str, catalog_item_id: str) -> bytes:
        """
        Gets the ownership token.
        Unused but kept for the global API reference.
        :param namespace:  namespace
        :param catalog_item_id: catalog item id
        :return: The ownership token.
        """
        user_id = self.user.get('account_id')
        url = f'https://{self._ecommerce_host}/ecommerceintegration/api/public/platforms/EPIC/identities/{user_id}/ownershipToken'
        r = self.session.post(url, data=dict(nsCatalogItemId=f'{namespace}:{catalog_item_id}'), timeout=self.request_timeout)
        r.raise_for_status()
        return r.content

    def get_external_auths(self) -> dict:
        """
        Gets the external auths.
        Unused but kept for the global API reference.
        :return: The external auths using json format.
        """
        user_id = self.user.get('account_id')
        url = f'https://{self._oauth_host}/account/api/public/account/{user_id}/externalAuths'
        r = self.session.get(url, timeout=self.request_timeout)
        r.raise_for_status()
        return r.json()

    def get_item_assets(self, platform='Windows', label='Live'):
        """
        Gets the item assets.
        :param platform: platform to get assets for
        :param label: label of the assets
        :return: The item assets using json format.
        """
        url = f'https://{self._launcher_host}/launcher/api/public/assets/{platform}'
        r = self.session.get(url, params=dict(label=label), timeout=self.request_timeout)
        r.raise_for_status()
        return r.json()

    def get_item_manifest(self, namespace, catalog_item_id, app_name, platform='Windows', label='Live') -> dict:
        """
        Gets the item manifest.
        :param namespace:  namespace
        :param catalog_item_id: catalog item id
        :param app_name: app name
        :param platform: platform to get manifest for
        :param label: label of the manifest
        :return: The item manifest using json format.
        """
        url = f'https://{self._launcher_host}/launcher/api/public/assets/v2/platform/{platform}/namespace/{namespace}/catalogItem/{catalog_item_id}/app/{app_name}/label/{label}'
        r = self.session.get(url, timeout=self.request_timeout)
        r.raise_for_status()
        return r.json()

    def get_launcher_manifests(self, platform='Windows', label: str = None) -> dict:
        """
        Gets the launcher manifests.
        Unused but kept for the global API reference.
        :param platform: platform to get manifests for
        :param label: label of the manifests
        :return: The launcher manifests using json format.
        """
        url = f'https://{self._launcher_host}/launcher/api/public/assets/v2/platform/{platform}/launcher'
        r = self.session.get(url, timeout=self.request_timeout, params=dict(label=label if label else self._label))
        r.raise_for_status()
        return r.json()

    def get_user_entitlements(self) -> dict:
        """
        Gets the user entitlements.
        Unused but kept for the global API reference.
        :return: The user entitlements using json format.
        """
        user_id = self.user.get('account_id')
        url = f'https://{self._entitlements_host}/entitlement/api/account/{user_id}/entitlements'
        r = self.session.get(url, params=dict(start=0, count=5000), timeout=self.request_timeout)
        r.raise_for_status()
        return r.json()

    def get_item_info(self, namespace: str, catalog_item_id: str, timeout: float = None) -> (dict, int):
        """
        Gets the item info.
        :param namespace: Namespace of the item
        :param catalog_item_id: Catalog item id of the item
        :param timeout: Timeout for the request
        :return: (The item info, status code)
        """
        url = f'https://{self._catalog_host}/catalog/api/shared/namespace/{namespace}/bulk/items'
        r = self.session.get(
            url,
            params=dict(
                id=catalog_item_id, includeDLCDetails=True, includeMainGameDetails=True, country=self.country_code, locale=self.language_code
            ),
            timeout=timeout or self.request_timeout
        )
        r.raise_for_status()
        return r.json().get(catalog_item_id, None), r.status_code

    def get_artifact_service_ticket(self, sandbox_id: str, artifact_id: str, label='Live', platform='Windows') -> dict:
        """
        Gets the artifact service ticket.
        Unused but kept for the global API reference.
        :param sandbox_id: sandbox id
        :param artifact_id: artifact id
        :param label: label
        :param platform: platform to get ticket for
        :return: The artifact service ticket using json format.
        """
        # Based on EOS Helper Windows service implementation. Only works with anonymous EOS Helper session.
        # sandbox_id is the same as the namespace, artifact_id is the same as the app name
        url = f'https://{self._artifact_service_host}/artifact-service/api/public/v1/dependency/sandbox/{sandbox_id}/artifact/{artifact_id}/ticket'
        r = self.session.post(
            url,
            json=dict(label=label, expiresInSeconds=300, platform=platform),
            params=dict(useSandboxAwareLabel='false'),
            timeout=self.request_timeout
        )
        r.raise_for_status()
        return r.json()

    def get_item_manifest_by_ticket(self, artifact_id: str, signed_ticket: str, label='Live', platform='Windows') -> dict:
        """
        Gets the item manifest by ticket.
        Unused but kept for the global API reference.
        :param artifact_id: artifact id
        :param signed_ticket: signed ticket
        :param label: the label
        :param platform: platform to get manifest for
        :return: The item manifest by ticket using json format.
        """
        # Based on EOS Helper Windows service implementation.
        url = f'https://{self._launcher_host}/launcher/api/public/assets/v2/by-ticket/app/{artifact_id}'
        r = self.session.post(url, json=dict(platform=platform, label=label, signedTicket=signed_ticket), timeout=self.request_timeout)
        r.raise_for_status()
        return r.json()

    def get_library_items(self, include_metadata=True) -> list:
        """
        Gets the library items.
        :param include_metadata: Whether to include metadata
        :return: The library items
        """
        records = []
        url = f'https://{self._library_host}/library/api/public/items'
        r = self.session.get(url, params=dict(includeMetadata=include_metadata), timeout=self.request_timeout)
        r.raise_for_status()
        j = r.json()
        records.extend(j['records'])

        # Fetch remaining library entries as long as there is a cursor
        url = f'https://{self._library_host}/library/api/public/items'
        while cursor := j['responseMetadata'].get('nextCursor', None):
            r = self.session.get(url, params=dict(includeMetadata=include_metadata, cursor=cursor), timeout=self.request_timeout)
            r.raise_for_status()
            j = r.json()
            records.extend(j['records'])

        return records

    def find_asset_url(self, asset_name: str, timeout=10.0) -> []:
        """
        Find the asset url from the asset name by searching the asset name in the unreal engine marketplace
        :param asset_name: asset name to search
        :param timeout: timeout for the request
        :return: (The asset url, the asset name (converted or found), the grab result code)
        """
        # remove the suffix _EngineVersion (ex _4.27) at the end of the name to have a valid search value
        regex = r"_[4|5]\.\d{1,2}$"
        converted_name = re.sub(regex, '', asset_name, 0)
        # Replace ' ' by '%20'
        converted_name = converted_name.replace(' ', '%20')
        # SnakeCase
        # converted_name = inflection.underscore(converted_name)
        # Lower case
        converted_name = converted_name.lower()
        # Replace '_' by '-'
        # converted_name = converted_name.replace('_', '-')

        # remove some not alphanumeric cars (NOT ALL, keep %)
        entry_list = [':', ',', '.', ';', '=', '?', '!', '#', "/", "$", "€"]
        for entry in entry_list:
            converted_name = converted_name.replace(entry, '')

        url = ''
        asset_slug = converted_name
        search_url_root = f'https://{self._search_url}/assets?keywords='
        search_url_full = search_url_root + converted_name
        try:
            r = self.session.get(search_url_full, timeout=timeout)
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

    #  get the extras data of an asset (price, review...)
    def get_assets_extras(self, asset_name: str, asset_title: str, timeout=10.0, verbose_mode=False) -> dict:
        """
        Get the extras data of an asset (price, review...)
        :param asset_name: name of the asset
        :param asset_title: title of the asset
        :param timeout: connection timeout
        :param verbose_mode: verbose mode
        :return: a dict with the extras data
        """
        not_found_price = 0.0
        not_found_review = 0.0
        supported_versions = ''
        page_title = ''
        no_result = create_empty_assets_extras(asset_name=asset_name)

        # try to find the url of the asset by doing a search in the marketplace
        asset_url, asset_slug, error_code = self.find_asset_url(asset_title, timeout)
        if asset_url == '' or error_code != GrabResult.NO_ERROR.name:
            self.log.info('No result found for grabbing data.\nThe asset name that has been searched for has been stored in the "Page title" Field')
            no_result['grab_result'] = error_code
            no_result['page_title'] = asset_slug
            return no_result
        try:
            response = self.session.get(asset_url)  # when using session, we are already logged in Epic game
            response.raise_for_status()
            self.log.info(f'Grabbing extras data for {asset_name}')
        except requests.exceptions.RequestException as error:
            self.log.warning(f'Can not get extras data for {asset_name}:{error!r}')
            self.log.info('No result found for grabbing data.\nThe asset name that has been searched for has been stored in the "Page title" Field')
            no_result['grab_result'] = error_code
            no_result['page_title'] = asset_slug
            return no_result

        soup_logged = BeautifulSoup(response.text, 'html.parser')

        price = not_found_price
        discount_price = not_found_price

        search_for_price = True

        # check if already owned
        owned = False
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
                owned = True
                if verbose_mode:
                    self.log.info(f'{asset_name} is already owned')
                # grab the price on a non logged soup (price will be available on that page only)
                try:
                    response = requests.get(asset_url)  # not using session, so not logged in Epic game
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
                # notes:
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
            (price-discount_price) / price * 100.0
        )
        discounted = (discount_price < price) or discount_percentage > 0.0

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
            'grab_result': error_code,
        }
