import logging
from pprint import pformat

from utils import cookies_repr


async def on_request_chunk_sent(session, trace_config_ctx, params):
     logging.debug('Request body chunk: %s', params.chunk.decode())


async def on_request_redirect(session, trace_config_ctx, params):
    logging.debug('Redirect: '
                  + params.method
                  + ' '
                  + str(params.url))
    logging.debug('Request Headers:\n' + pformat(params.response.request_info.headers.items()))
    logging.debug('%s %s', params.response.status, params.response.reason)
    logging.debug('Response Headers:\n' + pformat(params.response.headers.items()))
    logging.debug('Response Body:\n' + await params.response.text())
    logging.debug('Session Cookies:\n' + cookies_repr(session.cookie_jar))


async def on_request_end(session, trace_config_ctx, params):
    logging.debug('Link: '
                  + params.response.request_info.method
                  + ' '
                  + str(params.response.request_info.url))
    logging.debug('Request Headers:\n' + pformat(params.response.request_info.headers.items()))
    logging.debug('%s %s', params.response.status, params.response.reason)
    logging.debug('Response Headers:\n' + pformat(params.response.headers.items()))
    logging.debug('Response Body:\n' + await params.response.text())