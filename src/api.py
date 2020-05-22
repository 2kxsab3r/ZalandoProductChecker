import logging
import aiohttp.hdrs

from enum import IntEnum
from dataclasses import dataclass, field
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
    ACCESSORIES_URL = INDEX_URL / 'accessories/__size-One---size/'
    CART_URL = INDEX_URL / 'cart'
    CHK_CONFIRM_URL = INDEX_URL / 'checkout/confirm'
    CHK_ADDRESS_URL = INDEX_URL / 'checkout/address'
    API_LOGIN_URL = INDEX_URL / 'api/reef/login'
    API_SCHEMA_URL = API_LOGIN_URL / 'schema'
    API_CONSENTS = INDEX_URL / 'api/consents'
    API_SIZERECO = INDEX_URL / 'api/pdp/sizereco'
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

    login: str
    password: str
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
            'Accept': '*/*',
            'Content-Type': 'text/plain;charset=UTF-8',
            'Referer': referer,
        }
        if method == aiohttp.hdrs.METH_POST:
            headers.update({'Origin': self.INDEX_URL.origin()})
        resp = await self.session.request(method, self.RESR_URL, data=sensor_payload)

    async def login_page(self):
        logging.info('getting a login page')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Upgrade-Insecure-Requestshttps://www.youtube.com/watch?v=ZJ7FGBDErXY&list=PLoYlC0wSPJWaPvMrcGOs7veNzQ6_fE1kn&index=22': '1'
        }
        resp = await self.session.get(self.LOGIN_URL, headers=headers)
        return self._cookies['frsx'].value, self._cookies['Zalando-Client-Id'].value, resp.headers['x-zalando-child-request-id']

    async def api_consents(self, state: CookiePolicyState, xsrf):
        logging.info('consents api request')
        headers = {
            'Accept': '*/*',
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
            'Accept': 'application/json',
            'Referer': str(self.LOGIN_URL),
            'Content-Type': 'application/json',
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

    async def api_logout(self):  # todo on exit
        pass

    async def api_sizereco(self, xsrf, referer, simple_sku, silhouette, tgroup, version, gender):
        logging.info('sizereco api request')
        headers = {
            'Accept': 'application/json',
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        data = {
          "configSku": simple_sku.lstrip('0ONE000'),
          "isSizeFlagApplicable": False,
          "isSizeRecoApplicable": False,
          "isSizeTableApplicable": True,
          "isSizeProfileApplicable": False,
          "isSizeFinderApplicable": False,
          "customerHash": None,
          "availableSimpleSkus": [simple_sku],
          "silhouette": silhouette,
          "targetGroup": tgroup,
          "version": version,
          "gender": gender,
          "localSizeType": "UK"
        }
        resp = await self.session.post(self.API_SIZERECO, headers=headers, json=data)

    async def api_cart(self, xsrf, referer, simple_sku):
        logging.info('cart api request')
        headers = {
            'Accept': 'application/json',
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.post(self.API_CART, headers=headers,
                                       json={'simpleSku': simple_sku, 'anonymous': 'false'})

    async def api_cart_count(self, xsrf, referer):
        logging.info('cart count api request')
        headers = {
            'Accept': '*/*',
            'Referer': str(referer),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
        }
        resp = await self.session.get(self.API_CART_COUNT, headers=headers)

    async def api_cart_details(self, xsrf, referer):
        logging.info('cart details api request')
        headers = {
            'Accept': '*/*',
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
            'Accept': 'application/json',
            'Referer': str(self.CHK_ADDRESS_URL),
            'Origin': str(self.INDEX_URL.origin()),
            'x-xsrf-token': xsrf,
            'x-zalando-header-mode': 'desktop',
            'x-zalando-footer-mode': 'desktop',
            'x-zalando-checkout-app': 'web',
        }
        resp = await self.session.post(self.API_NEXT_STEP, headers=headers,
                                       json={'simpleSku': simple_sku, 'ids': []})

    async def myaccount_page(self):
        logging.info('getting a myaccount page')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': str(self.LOGIN_URL),
            'Upgrade-Insecure-Requests': '1'
            }
        resp = await self.session.get(self.MYACCOUNT_URL, headers=headers)

    async def one_size_accessories_page(self):
        logging.info('getting a accessories page')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': str(self.MYACCOUNT_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(self.ACCESSORIES_URL, headers=headers)
        html = await resp.text()
        return html

    async def product_page(self, url: str):
        logging.info('getting a product page')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': str(self.ACCESSORIES_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(url, headers=headers)
        html = await resp.text()
        return html

    async def cart_page(self, referer):
        logging.info('getting a cart page')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': str(referer),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(self.CART_URL, headers=headers)
        html = await resp.text()
        return html

    async def checkout_confirm_page(self):
        logging.info('getting a checkout confirm page')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': str(self.CART_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(self.CHK_CONFIRM_URL, headers=headers)
        html = await resp.text()
        return html

    async def payment_session_page(self, url):
        logging.info('getting a payment session page')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Host': URL(url).host,
            'Referer': str(self.CHK_ADDRESS_URL),
            'Upgrade-Insecure-Requests': '1'
        }
        resp = await self.session.get(url, headers=headers)

    async def purchase(self):
        pass
