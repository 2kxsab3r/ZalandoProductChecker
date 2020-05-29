import asyncio
from random import randint


class Delay:
    API = 1
    PAGE = 2
    PAYMENT = 3
    CART = 4

    @staticmethod
    def make(category):
        if category == Delay.API:
            delay = randint(200, 300)
        elif category == Delay.PAGE:
            delay = randint(500, 1800)
        elif category == Delay.PAYMENT:
            delay = randint(1017, 1903)
        elif category == Delay.CART:
            delay = randint(7031, 8023)
        return delay * 10 ** -3


async def sleep(delay: Delay):
    await asyncio.sleep(Delay.make(delay))


def make_ctx(api):
    return hex(hash(api)).lstrip('-')


def cookies_repr(cookie_jar, sep='\n'):
    return f'{sep}'.join(c.output(header='') for c in cookie_jar)
