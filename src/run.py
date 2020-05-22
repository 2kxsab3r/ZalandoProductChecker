import sys
import csv
import asyncio
import aiohttp.hdrs

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType
from contextvars import ContextVar
from aiohttp import ClientSession, ClientTimeout, TraceConfig
from yarl import URL
from api import ZalandoAPI
from tracing import on_request_chunk_sent, on_request_redirect, on_request_end
from utils import make_ctx, Delay, sleep
from parsing import *


TIMEOUT = 5
SESSION_TIMEOUT = 30
ctx = ContextVar('ctx', default='MAINCTX')


def read_csv(file):
    reader = csv.DictReader(file)
    return [row for row in reader][:1]  # todo remove


async def set_redirect_cookie(session, trace_config_ctx, params):  # todo
    logging.info('set redirect cookies')
    

class PurchasingTask:

    def __init__(self, api_data):
        trace_config = TraceConfig()
        trace_config.on_request_end.append(on_request_end)
        trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
        trace_config.on_request_redirect.extend(set_redirect_cookie, on_request_redirect)
        self.session = ClientSession(raise_for_status=False,
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
        xsrf, client_id, child_request_id1 = await self.api.login_page()
        await self._resources(self.api.LOGIN_URL)
        # logging.debug('Child request id: %s', child_request_id1)
        # child_request_id2 = await self.api.api_consents(CookiePolicyState.INIT, xsrf)
        # logging.debug('Child request id: %s', child_request_id2)
        # child_request_id3 = await self.api.api_consents(CookiePolicyState.ACCEPT, xsrf)
        # logging.debug('Child request id: %s', child_request_id3)
        await self.api.api_schema(xsrf, client_id, child_request_id1)
        await sleep(Delay.API)
        await self.api.api_login(xsrf, client_id, child_request_id1)
        logging.info('logging in is finished')
        return xsrf

    async def decrease_steps(self, xsrf):
        logging.info('start steps decreasing')
        # await self._resources(self.api.LOGIN_URL)
        await self.api.myaccount_page()
        await self._resources(self.api.MYACCOUNT_URL)

        html = await self.api.one_size_accessories_page()
        # navigation re
        # quest
        # brands request
        product_url = find_rand_product_url(html)
        product_url = ZalandoAPI.INDEX_URL.join(URL(product_url))
        await self._resources(self.api.ACCESSORIES_URL)

        html = await self.api.product_page(product_url)
        product_id, silhouette, tgroup, version, gender = find_product_params(html)
        await self._resources(product_url)
        # navigation request
        # sizereco request
        # check-whishlist request
        # brands request
        # reviews request
        # summaries request

        await self.api.api_sizereco(xsrf, product_url, product_id, silhouette, tgroup, version, gender)
        await self.api.api_cart(xsrf, product_url, product_id)
        await sleep(Delay.API)
        await self.api.api_cart_count(xsrf, product_url)
        await sleep(Delay.API)
        await self.api.api_cart_details(xsrf, product_url)
        await sleep(Delay.API)
        html = await self.api.cart_page(product_url)
        cart_id, flow_id = find_redeem_params(html)
        await self._resources(self.api.CART_URL)
        await self.api.api_redeem(xsrf, cart_id, flow_id)  # discount may be invalid
        # navigation request
        # cmag request
        # reco request
        # check-whishlist request
        html = await self.api.checkout_confirm_page() # 302 /checkout/address
        address_id = find_address_id(html)
        await self._resources(self.api.CHK_ADDRESS_URL)
        # cmag

        await self.api.api_checkout_address_def(xsrf, address_id)
        pay_sel_session_url = await self.api.api_next_step(xsrf)
        await self.api.payment_session_page(pay_sel_session_url)  # todo change host
        # 307,303, 302: payment.domain/selection, payment.domain/payment-complete, /checkout/confirm
        await self._resources(self.api.CHK_CONFIRM_URL)

        await self.api.api_remove_item(xsrf, product_id)
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
            #todo result checking for errors
        except Exception as e:
            logging.exception('')

    logging.info('done')


if __name__ == '__main__':
    import colorama
    colorama.init(autoreset=True)

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('csv', type=FileType('r'), help='absolute or relative to the current working directory path of a csv file')
    parser.add_argument('--timeout', type=int,  default=TIMEOUT, help='polling time in seconds to wait for a next monitoring request')
    parser.add_argument('--log-level', default='info', choices=list(n.lower() for n in logging._nameToLevel), help="set the logging level")
    args = parser.parse_args()

    logging.basicConfig(level=logging._nameToLevel[args.log_level.upper()], stream=sys.stdout, format='[%(asctime)s %(name)s %(levelname)s] %(message)s',
                        datefmt='%m-%d %H:%M:%S')
    asyncio.run(main(args.csv))