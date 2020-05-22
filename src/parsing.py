import logging
import json

from random import choice
from urllib.parse import unquote
from lxml import etree


def find_rand_product_url(text):
    html = etree.HTML(text)
    product_links = html.xpath('//z-grid-item[starts-with(@class, "cat_card")]//a')
    return choice(product_links).attrib['href']


def find_redeem_params(text):
    html = etree.HTML(text)
    cart_data_divs = html.xpath('//div[@id="app"]')
    count = len(cart_data_divs)
    if count != 1:  # todo cary out to a class
        logging.warning('%s divs. Cart data got from an undefined.')
    data = cart_data_divs[0].attrib['data-data']
    params = unquote(data)
    params = json.loads(params)
    cart_id = params['cart']['id']
    flow_id = params['metadata']['flowId']
    return cart_id, flow_id


def find_product_params(text):
    html = etree.HTML(text)
    prod_data_divs = html.xpath('//script[@id="z-vegas-pdp-props"]')
    data: str = prod_data_divs[0].text
    data = data.lstrip('<![CDATA')
    data = data.rstrip(']>')
    params = json.loads(data)
    units = params['model']['articleInfo']['units']
    id = next(filter(lambda u: u['available'], units))['id']
    silhouette = params['model']['articleInfo']['silhouette_code']
    tgroup = gender = params['model']['articleInfo']['targetGroups']['gender']
    version = params['model']['sizeInfo']['sizeRecoAlgoVersion']
    return id, silhouette, tgroup, version, gender


def find_address_id(text):
    html = etree.HTML(text)
    addr_data_divs = html.xpath('//div[@data-props]')
    count = len(addr_data_divs)
    if  count != 1:
        logging.warning('%s divs. Address data got from an undefined.')
    data = addr_data_divs[0].attrib['data-props']
    params = unquote(data)
    params = json.loads(params)
    id = params['model']['addressDetails']['defaultShippingAddress']['id']
    return id