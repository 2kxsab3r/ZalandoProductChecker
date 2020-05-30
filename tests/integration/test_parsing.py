from parsing import (find_product_params, find_address_id, find_rand_product_url,
                     find_redeem_params)


def test_find_product_params():
    with open('../files/html/product, only size.html') as file:
        id, silhouette, version, uid_hash = find_product_params(file.read())
        assert id == 'PO252E00N-B110ONE000'
        assert  silhouette == 'headgear'
        assert version == 'MD1'
        assert uid_hash == '4b9f18396dbdd59e2aa893a8c347b012'


def test_find_address_id():
    with open('../files/html/checkout/address.html') as file:
        id = find_address_id(file.read())
        assert id == '17530966'


def test_find_rand_product_url():
    with open('../files/html/accessories.html') as file:
        url: str = find_rand_product_url(file.read())
        assert url.startswith('/')
        assert url.endswith('.html')


def test_find_redeem_params():
    with open('../files/html/cart.html') as file:
        cart_id, flow_id = find_redeem_params(file.read())
        assert cart_id == '6870e7421eae62ea11d603282d71904a224a9cb9bc884ed40b28eaa5b60c8fc4'
        assert flow_id == 'TuOM0bMmS78Il9y8'
