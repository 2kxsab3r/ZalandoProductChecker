import asyncio
from random import randint


class Delay:
    API = 1
    PAGE = 2
    PAYMENT = 3
    CART = 4

    DEFAULTS = {API: (200, 300),
                PAGE: (500, 1800),
                PAYMENT: (1017, 1903),
                CART: (7031, 8023)}

    @staticmethod
    def make(category):
        if category == Delay.API:
            delay = randint(*Delay.DEFAULTS[Delay.API])
        elif category == Delay.PAGE:
            delay = randint(*Delay.DEFAULTS[Delay.PAGE])
        elif category == Delay.PAYMENT:
            delay = randint(*Delay.DEFAULTS[Delay.PAYMENT])
        elif category == Delay.CART:
            delay = randint(*Delay.DEFAULTS[Delay.CART])
        return delay * 10 ** -3


async def sleep(delay: Delay):
    await asyncio.sleep(Delay.make(delay))


def make_ctx(api):
    return hex(hash(api)).lstrip('-')


def cookies_repr(cookie_jar, sep='\n'):
    return f'{sep}'.join(c.output(header='') for c in cookie_jar)
