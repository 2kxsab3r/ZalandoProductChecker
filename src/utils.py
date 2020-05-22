import asyncio

from random import randint


def make_ctx(api):
    return hex(hash(api)).lstrip('-')


class Delay:
    API = 1
    PAGE = 2

    @staticmethod
    def make(category):
        if category == Delay.API:
            delay = randint(130, 210)
        elif category == Delay.PAGE:
            delay = randint(1400, 1800)
        return delay * 10 ** -3


async def sleep(delay: Delay):
    await asyncio.sleep(Delay.make(delay))
