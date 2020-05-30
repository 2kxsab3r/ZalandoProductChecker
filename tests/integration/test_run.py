import asyncio
from unittest.mock import patch, AsyncMock, Mock

from run import PurchasingTask
from utils import Delay


@patch('run.find_redeem_params')
@patch('run.find_rand_product_url')
@patch('run.find_address_id')
@patch('run.find_product_params')
@patch('run.ClientSession')
@patch.dict('run.Delay.DEFAULTS', {k: (1,1) for k in Delay.DEFAULTS})
def test_purchasing_task(session_mock, find_product_params_mock, find_address_id_mock, find_rand_product_url_mock,
                         find_redeem_params_mock):
    # vars
    api_data = {'login': 'login',
                'password': 'password',
                'id': 'od',
                'dcode': 'dcode',
                'size': 'size'}
    product_url = 'product/url'
    product_id = 'product_id'
    silhouette = 'silhouette'
    version = 'version'
    uid_hash = 'uid_hash'
    cart_id = 'cart_id'
    flow_id = 'flow_id'
    address_id = 'address_id'
    cart_count = 1
    accessories_page_html = 'accessories page html'
    product_page_html = 'product page html'
    cart_page_html = 'cart page html'
    checkout_confirm_page_html = 'checkout confirm page html'
    api_next_step_json = {'url': 'api/next/url'}

    # mocks
    cookies = {'frsx': Mock(value='frsx value'), 'Zalando-Client-Id': Mock(value='zclient id')}
    cookie_jar = Mock(filter_cookies=Mock(return_value=cookies))
    find_rand_product_url_mock.return_value = product_url
    find_product_params_mock.return_value = product_id, silhouette, version, uid_hash
    find_redeem_params_mock.return_value = cart_id, flow_id
    find_address_id_mock.return_value = address_id
    get_responses = [Mock(headers={'x-zalando-child-request-id': 'rid'}),
                     Mock(),
                     Mock(),
                     Mock(text=AsyncMock(return_value=accessories_page_html)),
                     Mock(text=AsyncMock(return_value=product_page_html)),
                     Mock(),
                     Mock(),
                     Mock(json=AsyncMock(return_value=cart_count)),
                     Mock(),
                     Mock(text=AsyncMock(return_value=cart_page_html)),
                     Mock(text=AsyncMock(return_value=checkout_confirm_page_html)),
                     Mock(json=AsyncMock(return_value=api_next_step_json)),
                     Mock(status=307, headers={'location': 'location/1'}),
                     Mock(status=303, headers={'location': 'location/2'}),
                     Mock(),
                     Mock(text=AsyncMock(return_value=cart_page_html)),
                     ]
    session_mock.return_value = AsyncMock(cookie_jar=cookie_jar,
                                          get=AsyncMock(side_effect=get_responses),
                                          post=AsyncMock(),
                                          request=AsyncMock())
    t = PurchasingTask(api_data)
    asyncio.run(t.run())

    find_rand_product_url_mock.assert_called_once_with(accessories_page_html)
    find_product_params_mock.assert_called_once_with(product_page_html)
    find_redeem_params_mock.assert_called_once_with(cart_page_html)
    find_address_id_mock.assert_called_once_with(checkout_confirm_page_html)
    assert t.session.closed
