import mock
import json
import unittest
import sys

sys.modules['MySQLdb'] = mock.Mock()
from charmhelpers.contrib.database import mysql  # noqa


class MysqlTests(unittest.TestCase):
    def setUp(self):
        super(MysqlTests, self).setUp()

    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password')
    @mock.patch.object(mysql.MySQLHelper, 'grant_exists')
    @mock.patch.object(mysql, 'relation_get')
    @mock.patch.object(mysql, 'related_units')
    @mock.patch.object(mysql, 'log')
    def test_get_allowed_units(self, mock_log, mock_related_units,
                               mock_relation_get,
                               mock_grant_exists,
                               mock_get_password):

        def mock_rel_get(unit, rid):
            if unit == 'unit/0':
                # Non-prefixed settings
                d = {'private-address': '10.0.0.1',
                     'hostname': 'hostA'}
            elif unit == 'unit/1':
                # Containing prefixed settings
                d = {'private-address': '10.0.0.2',
                     'dbA_hostname': json.dumps(['10.0.0.2', '2001:db8:1::2'])}
            elif unit == 'unit/2':
                # No hostname
                d = {'private-address': '10.0.0.3'}

            return d

        mock_relation_get.side_effect = mock_rel_get
        mock_related_units.return_value = ['unit/0', 'unit/1', 'unit/2']

        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        units = helper.get_allowed_units('dbA', 'userA')

        calls = [mock.call('dbA', 'userA', 'hostA'),
                 mock.call().__nonzero__(),
                 mock.call('dbA', 'userA', '10.0.0.2'),
                 mock.call().__nonzero__(),
                 mock.call('dbA', 'userA', '2001:db8:1::2'),
                 mock.call().__nonzero__(),
                 mock.call('dbA', 'userA', '10.0.0.3'),
                 mock.call().__nonzero__()]

        helper.grant_exists.assert_has_calls(calls)
        self.assertEqual(units, set(['unit/0', 'unit/1', 'unit/2']))


class PerconaTests(unittest.TestCase):

    def setUp(self):
        super(PerconaTests, self).setUp()

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    def test_parse_config_innodb_pool_fixed(self, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'innodb-buffer-pool-size': "50%",
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(mysql_config.get('innodb_buffer_pool_size'),
                         helper.human_to_bytes("50G"))

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    def test_parse_config_innodb_pool_not_set(self, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'innodb-buffer-pool-size': '',
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb_buffer_pool_size'),
            int(helper.human_to_bytes(mem.return_value) *
                helper.DEFAULT_INNODB_BUFFER_FACTOR))
