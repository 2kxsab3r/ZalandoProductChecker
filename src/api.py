import logging
from enum import IntEnum
from dataclasses import dataclass, field

import aiohttp.hdrs
from aiohttp import ClientSession
from yarl import URL


with open('payloads/cookie-policy-accept.json') as ifile, \
        open('payloads/cookie-policy-init.json') as afile, \
        open('payloads/sensor-data.json') as sfile:
    init_payload = ifile.read()
    accept_payload = afile.read()
    sensor_payload = sfile.read()


class CookiePolicyState(IntEnum):
    INIT = 1
    ACCEPT = 2

    @staticmethod
    def payload(state):
        if state == CookiePolicyState.INIT:
            return init_payload
        elif state == CookiePolicyState.ACCEPT:
            return accept_payload


@dataclass(unsafe_hash=True)
class ZalandoAPI:
    INDEX_URL = URL('https://www.zalando.co.uk')
    RESR_URL = INDEX_URL / 'resources/77fdb5043d236dc310c6074abbf38d'
    LOGIN_URL = INDEX_URL / 'login'
    MYACCOUNT_URL = INDEX_URL / 'myaccount'
    ACCESSORIES_URL = INDEX_URL / 'mens-hats-caps/__size-One---size/'
    CART_URL = INDEX_URL / 'cart'
    CHK_CONFIRM_URL = INDEX_URL / 'checkout/confirm'
    CHK_ADDRESS_URL = INDEX_URL / 'checkout/address'
    API_LOGIN_URL = INDEX_URL / 'api/reef/login'
    API_SCHEMA_URL = API_LOGIN_URL / 'schema'
    API_CONSENTS = INDEX_URL / 'api/consents'
    API_SIZERECO = INDEX_URL / 'api/pdp/sizereco'
    API_CHECK_WISHLIST = INDEX_URL / 'api/pdp/check-wishlist'
    API_PREFERENCE_BRANDS = INDEX_URL / 'api/customer-preference-api/preference-types/brands'
    API_CART = INDEX_URL / 'api/pdp/cart'
    API_CART_COUNT = INDEX_URL / 'api/navigation/cart-count'
    API_CART_DETAILS = INDEX_URL / 'api/cart/details'
    API_REDEEM = INDEX_URL / 'api/cart-fragment/redeem'
    API_CHK_ADDRESS_DEF = INDEX_URL / 'api/checkout/address/{id}/default'
    API_NEXT_STEP = INDEX_URL / 'api/checkout/next-step'
    API_REMOVE_ITEM = INDEX_URL / 'api/checkout/remove-confirmation-item'

    CONSTANT_HEADERS = {
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Host': INDEX_URL.host,
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0',
            'TE': 'Trailers',
            'Connection': 'close',  # https://stackoverflow.com/a/61436084
            'DNT': '1',  # https://stackoverflow.com/a/61436084
        }
    H_ACCEPT_TEXT = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    H_ACCEPT_ALL = '*/*'
    MIME_JSON = 'application/json'

    login: str
    password: str = field(repr=False)
    id: str
    dcode: str
    size: str
    session: ClientSession = field(repr=False, hash=False, compare=False)

    @property
    def _cookies(self):
        return self.session.cookie_jar.filter_cookies(self.INDEX_URL)

    async def resources(self, method, referer: str):
        logging.info('getting the resources')
        headers = {
            'Accept': self.H_ACCEPT_ALL,
            'Content-Type': 'text/plain;charset=UTF-8',
            'Referer': referer,
        }
        if method == aiohttp.hdrs.METH_POST:
            headers.update({'Origin': self.INDEX_URL.origin()})
        resp = await self.session.request(method, self.RESR_URL, data=sensor_payload)

    async def login_page(self):
        logging.info('getting a login page')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(self.LOGIN_URL, headers=headers)
        return self._cookies['frsx'].value, self._cookies['Zalando-Client-Id'].value, resp.headers['x-zalando-child-request-id']

    async def api_consents(self, state: CookiePolicyState, xsrf):
        logging.info('consents api request')
        headers = {
            'Accept': self.H_ACCEPT_ALL,
            'Referer': str(self.LOGIN_URL),
            'Origin': str(self.INDEX_URL.origin()),
            'Content-Type': 'text/plain;charset=UTF-8',
            'x-xsrf-token': xsrf
        }
        payload = CookiePolicyState.payload(state)
        resp = await self.session.post(self.API_CONSENTS, headers=headers, data=payload)
        return resp.headers['x-zalando-child-request-id']

    async def api_schema(self, xsrf, client_id, flow_id):
        logging.info('schema api request')
        headers = {
            'Accept': self.MIME_JSON,
            'Referer': str(self.LOGIN_URL),
            'Content-Type': self.MIME_JSON,
            'x-zalando-client-id': client_id,
            'x-zalando-render-page-uri': '/login',
            'x-zalando-request-uri': '/login',
            'x-flow-id': flow_id,
            'x-xsrf-token': xsrf,
            }
        resp = await self.session.get(self.API_SCHEMA_URL, headers=headers)

    async def api_login(self, xsrf, client_id, flow_id):
        logging.info('login api request')
        headers = {
            'Referer': str(self.LOGIN_URL),
            'Origin': str(self.INDEX_URL.origin()),
            'x-zalando-client-id': client_id,
            'x-zalando-render-page-uri': '/login',
            'x-zalando-request-uri': '/login',
            'x-flow-id': flow_id,
            'x-xsrf-token': xsrf,
            }
        resp = await self.session.post(self.API_LOGIN_URL, headers=headers,
                                       json={'username': self.login, 'password': self.password, 'wnaMode': 'shop'})

    async def api_logout(self):
        pass

    async def api_sizereco(self, xsrf, referer, simple_sku, silhouette, version, chash):
        logging.info('sizereco api request')
        headers = {
            'Accept': self.MIME_JSON,
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        data = {
          "configSku": simple_sku.rstrip('0ONE000'),
          "isSizeFlagApplicable": False,
          "isSizeRecoApplicable": False,
          "isSizeTableApplicable": True,
          "isSizeFinderApplicable": False,
          "customerHash": chash,
          "availableSimpleSkus": [simple_sku],
          "silhouette": silhouette,
          "targetGroup": "UNISEX",
          "version": version,
          "tableBounds": {
               "filters": [
                   {
                       "targetGroups": [
                           "MALE",
                           "FEMALE",
                           "UNISEX"
                       ],
                       "filterName": "matchStrictEqual"
                   }
               ],
               "units": [
                   {
                       "local": "One Size",
                       "local_type": "UK"
                   }
               ]
           },
          "localSizeType": "UK"
        }
        resp = await self.session.post(self.API_SIZERECO, headers=headers, json=data)

    async def api_check_wishlist(self, xsrf, referer, simple_sku):
        logging.info('check wishlist api request')
        headers = {
            'Accept': self.H_ACCEPT_ALL,
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.get(self.API_CHECK_WISHLIST, params={'configSku': simple_sku.rstrip('0ONE000')}, headers=headers)

    async def api_preference_brands(self, xsrf, referer):
        logging.info('preference brands api request')
        headers = {
            'Accept': self.H_ACCEPT_ALL,
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.get(self.API_PREFERENCE_BRANDS, headers=headers)

    async def api_cart(self, xsrf, referer, simple_sku):
        logging.info('cart api request')
        headers = {
            'Accept': self.MIME_JSON,
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.post(self.API_CART, headers=headers,
                                       json={'simpleSku': simple_sku, 'anonymous': False})

    async def api_cart_count(self, xsrf, referer):
        logging.info('cart count api request')
        headers = {
            'Accept': self.H_ACCEPT_ALL,
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.get(self.API_CART_COUNT, headers=headers)
        count = await resp.json()
        if count == 0:
            raise ValueError('Zero product count in a cart')

    async def api_cart_details(self, xsrf, referer):
        logging.info('cart details api request')
        headers = {
            'Accept': self.H_ACCEPT_ALL,
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.get(self.API_CART_DETAILS, headers=headers)

    async def api_redeem(self, xsrf, cart_id, flow_id):
        logging.info('redeem api request')
        headers = {
            'Referer': str(self.CART_URL),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.post(self.API_REDEEM, headers=headers,
                                       json={'cartId': cart_id, 'code': self.dcode, 'pageRenderFlowId': flow_id})

    async def api_checkout_address_def(self, xsrf, id):
        logging.info('checkout address api request')
        headers = {
            'Referer': str(self.CHK_ADDRESS_URL),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
            'x-zalando-header-mode': 'desktop',
            'x-zalando-footer-mode': 'desktop',
            'x-zalando-checkout-app': 'web',
        }
        url = self.API_CHK_ADDRESS_DEF.with_path(self.API_CHK_ADDRESS_DEF.path.format(id=id))
        resp = await self.session.post(url, headers=headers, json={'isDefaultShipping': True})

    async def api_next_step(self, xsrf):
        logging.info('next step api request')
        headers = {
            'Referer': str(self.CHK_ADDRESS_URL),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
            'x-zalando-header-mode': 'desktop',
            'x-zalando-footer-mode': 'desktop',
            'x-zalando-checkout-app': 'web',
        }
        resp = await self.session.get(self.API_NEXT_STEP, headers=headers)
        data = await resp.json()
        return data['url']

    async def api_remove_item(self, xsrf, simple_sku):
        logging.info('remove item api request')
        headers = {
            'Accept': self.MIME_JSON,
            'Referer': str(self.CHK_CONFIRM_URL),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
            'x-zalando-header-mode': 'desktop',
            'x-zalando-footer-mode': 'desktop',
            'x-zalando-checkout-app': 'web',
        }
        resp = await self.session.post(self.API_REMOVE_ITEM, headers=headers,
                                       json={'simpleSku': simple_sku, 'ids': []})

    async def myaccount_page(self):
        logging.info('getting a myaccount page')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Referer': str(self.LOGIN_URL),
            'Upgrade-Insecure-Requests': '1'
            }
        resp = await self.session.get(self.MYACCOUNT_URL, headers=headers)

    async def one_size_accessories_page(self):
        logging.info('getting a accessories page')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Referer': str(self.MYACCOUNT_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(self.ACCESSORIES_URL, headers=headers)
        html = await resp.text()
        return html

    async def product_page(self, url: str):
        logging.info('getting a product page')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Referer': str(self.ACCESSORIES_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(url, headers=headers)
        html = await resp.text()
        return html

    async def cart_page(self, referer):
        logging.info('getting a cart page')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Referer': str(referer),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(self.CART_URL, headers=headers)
        html = await resp.text()
        return html

    async def checkout_confirm_page(self):
        logging.info('getting a checkout confirm page')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Referer': str(self.CART_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(self.CHK_CONFIRM_URL, headers=headers)
        html = await resp.text()
        return html

    async def payment_session(self, url):
        logging.info('getting a payment session')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Host': URL(url).host,
            'Referer': str(self.CHK_ADDRESS_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(url, headers=headers, allow_redirects=False)
        if resp.status != 307:
            raise ValueError(f'Invalid redirection status {resp.status}')
        return resp.headers['location']

    async def payment_selection(self, url):
        logging.info('getting a payment selection')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Host': url.host,
            'Referer': str(self.CHK_ADDRESS_URL),
            'Upgrade-Insecure-Requests': '1',
        }
        resp = await self.session.get(url, headers=headers, allow_redirects=False)

        if resp.status != 303:
            raise ValueError(f'Invalid redirection status {resp.status}')
        return resp.headers['location']

    async def payment_complete(self, url):
        logging.info('getting a checkout payment complete')
        headers = {
            'Accept': self.H_ACCEPT_TEXT,
            'Host': URL(url).host,
            'Referer': str(self.CHK_ADDRESS_URL),
            'Upgrade-Insecure-Requests': '1',
        }
        resp = await self.session.get(url, headers=headers)
        resp.raise_for_status()

    async def purchase(self):
        pass
