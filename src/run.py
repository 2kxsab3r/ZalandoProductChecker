import sys
import csv
import asyncio
import logging
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType
from contextvars import ContextVar

import aiohttp.hdrs
from aiohttp import ClientSession, ClientTimeout, TraceConfig
from yarl import URL

from api import ZalandoAPI
from tracing import on_request_chunk_sent, on_request_redirect, on_request_end
from utils import make_ctx, Delay, sleep
from parsing import find_product_params, find_address_id, find_rand_product_url, find_redeem_params


TIMEOUT = 5
SESSION_TIMEOUT = None
ctx = ContextVar('ctx', default='MAINCTX')


def read_csv(file):
    reader = csv.DictReader(file)
    return [row for row in reader][:1]  # todo remove


class PurchasingTask:

    def __init__(self, api_data):
        trace_config = TraceConfig()
        trace_config.on_request_end.append(on_request_end)
        trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
        trace_config.on_request_redirect.append(on_request_redirect)
        self.session = ClientSession(raise_for_status=True,
                                     headers=ZalandoAPI.CONSTANT_HEADERS,
                                     timeout=ClientTimeout(total=SESSION_TIMEOUT),
                                     trace_configs=[trace_config])
        self.api = ZalandoAPI(session=self.session, **api_data)
        ctx.set(make_ctx(self.api))  # todo не в корутине, может быть отрицательным
        logging.info('task %s for %s is initialized', ctx.get(), self.api)

    async def _resources(self, referer):
        await sleep(Delay.PAGE)
        await self.api.resources(aiohttp.hdrs.METH_GET, str(referer))
        await sleep(Delay.PAGE)
        await self.api.resources(aiohttp.hdrs.METH_POST, str(referer))
        await sleep(Delay.PAGE)

    async def log_in(self):
        logging.info('start logging in')
        xsrf, client_id, child_request_id = await self.api.login_page()
        await self._resources(self.api.LOGIN_URL)
        # child_request_id2 = await self.api.api_consents(CookiePolicyState.INIT, xsrf)
        # child_request_id3 = await self.api.api_consents(CookiePolicyState.ACCEPT, xsrf)
        await self.api.api_schema(xsrf, client_id, child_request_id)
        await sleep(Delay.API)
        await self.api.api_login(xsrf, client_id, child_request_id)
        logging.info('logging in is finished')
        return xsrf

    async def decrease_steps(self,  xsrf):
        logging.info('start steps decreasing')
        await self.api.myaccount_page()
        await self._resources(self.api.MYACCOUNT_URL)

        html = await self.api.one_size_accessories_page()
        product_url = find_rand_product_url(html)
        product_url = ZalandoAPI.INDEX_URL.join(URL(product_url))
        await self._resources(self.api.ACCESSORIES_URL)

        html = await self.api.product_page(product_url)
        product_id, silhouette, version, uid_hash = find_product_params(html)
        await self._resources(product_url)

        await self.api.api_sizereco(xsrf, product_url, product_id, silhouette, version, uid_hash)
        await sleep(Delay.API)
        await self.api.api_check_wishlist(xsrf, product_url, product_id)
        await sleep(Delay.API)
        await self.api.api_preference_brands(xsrf, product_url)
        await sleep(Delay.CART)
        await self.api.api_cart(xsrf, product_url, product_id)
        await sleep(Delay.API)
        await self.api.api_cart_count(xsrf, product_url)
        await sleep(Delay.API)
        await self.api.api_cart_details(xsrf, product_url)
        await sleep(Delay.API)
        html = await self.api.cart_page(product_url)
        cart_id, flow_id = find_redeem_params(html)
        await self._resources(self.api.CART_URL)

        # discount may be expired/invalid, or product already has it
        await self.api.api_redeem(xsrf, cart_id, flow_id)
        await sleep(Delay.API)
        html = await self.api.checkout_confirm_page()  # 302 /checkout/address
        address_id = find_address_id(html)
        await self._resources(self.api.CHK_ADDRESS_URL)

        await self.api.api_checkout_address_def(xsrf, address_id)
        payment_session_url = URL(await self.api.api_next_step(xsrf))
        await sleep(Delay.API)
        # 307,303, 302: payment.domain/selection, payment.domain/payment-complete, /checkout/confirm
        location = await self.api.payment_session(payment_session_url)
        payment_selection_url = payment_session_url.with_path(location)
        await sleep(Delay.PAYMENT)
        location = await self.api.payment_selection(payment_selection_url)
        await sleep(Delay.PAYMENT)
        await self.api.payment_complete(location)
        await self._resources(self.api.CHK_CONFIRM_URL)

        await self.api.api_remove_item(xsrf, product_id)
        await sleep(Delay.PAGE)
        await self.api.cart_page(self.api.CHK_CONFIRM_URL)
        await self._resources(self.api.CART_URL)
        logging.info('steps decreasing is finished')

    async def monitor_purchase(self):
        logging.info('start monitoring')

    async def log_out(self):
        await self.api.api_logout()

    async def run(self):
        logging.info('task is running')
        xsrf = await self.log_in()
        await sleep(Delay.PAGE)
        await self.decrease_steps(xsrf)
        await self.monitor_purchase()
        await self.log_out()
        await self.session.close()
        logging.info('task is finished')


async def main(csv):
    logging.info('create tasks')
    tasks = []
    for api_data in read_csv(csv):
        task = asyncio.create_task(PurchasingTask(api_data).run())
        tasks.append(task)

    logging.info('wait for tasks completion')
    for f in asyncio.as_completed(tasks):
        try:
            res = await f
        except:
            logging.exception('')

    logging.info('done')


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('csv', type=FileType('r'), help='Absolute or relative to the current working directory path of a csv file')
    parser.add_argument('--timeout', type=int,  default=TIMEOUT, help='Polling time in seconds to wait for a next monitoring request')
    parser.add_argument('--log-level', default='info', choices=list(n.lower() for n in logging._nameToLevel), help="Set the logging level")
    args = parser.parse_args()

    logging.basicConfig(level=logging._nameToLevel[args.log_level.upper()], stream=sys.stdout,
                        format='[%(asctime)s %(name)s %(levelname)s] %(message)s', datefmt='%m-%d %H:%M:%S')
    asyncio.run(main(args.csv))