from testtools import TestCase
from mock import patch, call, MagicMock

import charmhelpers.contrib.openstack.ip as ip

TO_PATCH = [
    'config',
    'unit_get',
    'get_address_in_network',
    'is_clustered'
]


class TestConfig():

    def __init__(self):
        self.config = {}

    def set(self, key, value):
        self.config[key] = value

    def get(self, key):
        return self.config.get(key)


class IPTestCase(TestCase):

    def setUp(self):
        super(IPTestCase, self).setUp()
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        self.test_config = TestConfig()
        self.config.side_effect = self.test_config.get

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.openstack.ip.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_resolve_address_default(self):
        self.is_clustered.return_value = False
        self.unit_get.return_value = 'unit1'
        self.get_address_in_network.return_value = 'unit1'
        self.assertEquals(ip.resolve_address(), 'unit1')
        self.unit_get.assert_called_with('public-address')
        calls = [call('os-public-network'),
                 call('prefer-ipv6')]
        self.config.assert_has_calls(calls)
        self.get_address_in_network.assert_called_with(None, 'unit1')

    def test_resolve_address_default_internal(self):
        self.is_clustered.return_value = False
        self.unit_get.return_value = 'unit1'
        self.get_address_in_network.return_value = 'unit1'
        self.assertEquals(ip.resolve_address(ip.INTERNAL), 'unit1')
        self.unit_get.assert_called_with('private-address')
        calls = [call('os-internal-network'),
                 call('prefer-ipv6')]
        self.config.assert_has_calls(calls)
        self.get_address_in_network.assert_called_with(None, 'unit1')

    def test_resolve_address_public_not_clustered(self):
        self.is_clustered.return_value = False
        self.test_config.set('os-public-network', '192.168.20.0/24')
        self.unit_get.return_value = 'unit1'
        self.get_address_in_network.return_value = '192.168.20.1'
        self.assertEquals(ip.resolve_address(), '192.168.20.1')
        self.unit_get.assert_called_with('public-address')
        calls = [call('os-public-network'),
                 call('prefer-ipv6')]
        self.config.assert_has_calls(calls)
        self.get_address_in_network.assert_called_with(
            '192.168.20.0/24',
            'unit1')

    def test_resolve_address_public_clustered(self):
        self.is_clustered.return_value = True
        self.test_config.set('os-public-network', '192.168.20.0/24')
        self.test_config.set('vip', '192.168.20.100 10.5.3.1')
        self.assertEquals(ip.resolve_address(), '192.168.20.100')

    def test_resolve_address_default_clustered(self):
        self.is_clustered.return_value = True
        self.test_config.set('vip', '10.5.3.1')
        self.assertEquals(ip.resolve_address(), '10.5.3.1')
        self.config.assert_has_calls(
            [call('vip'),
             call('os-public-network')])

    def test_resolve_address_public_clustered_inresolvable(self):
        self.is_clustered.return_value = True
        self.test_config.set('os-public-network', '192.168.20.0/24')
        self.test_config.set('vip', '10.5.3.1')
        self.assertRaises(ValueError, ip.resolve_address)

    @patch.object(ip, 'resolve_address')
    def test_canonical_url_http(self, resolve_address):
        resolve_address.return_value = 'unit1'
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        self.assertTrue(ip.canonical_url(configs),
                        'http://unit1')

    @patch.object(ip, 'resolve_address')
    def test_canonical_url_https(self, resolve_address):
        resolve_address.return_value = 'unit1'
        configs = MagicMock()
        configs.complete_contexts.return_value = ['https']
        self.assertTrue(ip.canonical_url(configs),
                        'https://unit1')

    def test_endpoint_url(self):
        configs = MagicMock()
        configs.complete_contexts.return_value = ['https']

        self.test_config.set('public-address', 'public.example.com')
        self.test_config.set('internal-address', 'internal.example.com')
        self.test_config.set('admin-address', 'admin.example.com')

        endpoint = ip.public_endpoint(configs, '%s:%s/pub', 443)
        self.assertEqual('https://public.example.com:443/pub',
                         endpoint)

        endpoint = ip.internal_endpoint(configs, '%s:%s/internal', 443)
        self.assertEqual('https://internal.example.com:443/internal',
                         endpoint)

        endpoint = ip.admin_endpoint(configs, '%s:%s/admin', 443)
        self.assertEqual('https://admin.example.com:443/admin',
                         endpoint)

    @patch.object(ip, 'canonical_url')
    def test_endpoint_url_no_override(self, canonical_url):
        canonical_url.return_value = 'https://unit1'
        configs = MagicMock()
        configs.complete_contexts.return_value = ['https']

        endpoint = ip.endpoint_url(configs, '%s:%s/v1/AUTH_$(tenant_id)s', 443)
        self.assertEqual('https://unit1:443/v1/AUTH_$(tenant_id)s', endpoint)

    @patch.object(ip, 'resolve_address')
    @patch.object(ip, 'is_ipv6')
    def test_endpoint_url_no_override_ipv6(self, is_ipv6, resolve_address):
        resolve_address.return_value = 'unit1'
        is_ipv6.return_value = True
        configs = MagicMock()
        configs.complete_contexts.return_value = ['https']
        endpoint = ip.endpoint_url(configs, '%s:%s', 443, ip.ADMIN)
        self.assertEquals('https://[unit1]:443', endpoint)
