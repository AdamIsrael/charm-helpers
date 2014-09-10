import charmhelpers.contrib.openstack.context as context
import yaml
import json
import unittest
from copy import copy, deepcopy
from mock import (
    patch,
    Mock,
    MagicMock,
    call
)
from tests.helpers import patch_open


class FakeRelation(object):

    '''
    A fake relation class. Lets tests specify simple relation data
    for a default relation + unit (foo:0, foo/0, set in setUp()), eg:

        rel = {
            'private-address': 'foo',
            'password': 'passwd',
        }
        relation = FakeRelation(rel)
        self.relation_get.side_effect = relation.get
        passwd = self.relation_get('password')

    or more complex relations meant to be addressed by explicit relation id
    + unit id combos:

        rel = {
            'mysql:0': {
                'mysql/0': {
                    'private-address': 'foo',
                    'password': 'passwd',
                }
            }
        }
        relation = FakeRelation(rel)
        self.relation_get.side_affect = relation.get
        passwd = self.relation_get('password', rid='mysql:0', unit='mysql/0')
    '''

    def __init__(self, relation_data):
        self.relation_data = relation_data

    def get(self, attribute=None, unit=None, rid=None):
        if not rid or rid == 'foo:0':
            if attribute is None:
                return self.relation_data
            elif attribute in self.relation_data:
                return self.relation_data[attribute]
            return None
        else:
            if rid not in self.relation_data:
                return None
            try:
                relation = self.relation_data[rid][unit]
            except KeyError:
                return None
            if attribute in relation:
                return relation[attribute]
            return None

    def relation_ids(self, relation):
        return self.relation_data.keys()

    def relation_units(self, relation_id):
        if relation_id not in self.relation_data:
            return None
        return self.relation_data[relation_id].keys()

SHARED_DB_RELATION = {
    'db_host': 'dbserver.local',
    'password': 'foo'
}

SHARED_DB_RELATION_SSL = {
    'db_host': 'dbserver.local',
    'password': 'foo',
    'ssl_ca': 'Zm9vCg==',
    'ssl_cert': 'YmFyCg==',
    'ssl_key': 'Zm9vYmFyCg==',
}

SHARED_DB_CONFIG = {
    'database-user': 'adam',
    'database': 'foodb',
}

SHARED_DB_RELATION_NAMESPACED = {
    'db_host': 'bar',
    'quantum_password': 'bar2'
}

SHARED_DB_RELATION_ACCESS_NETWORK = {
    'db_host': 'dbserver.local',
    'password': 'foo',
    'access-network': '10.5.5.0/24',
    'hostname': 'bar',
}


IDENTITY_SERVICE_RELATION_HTTP = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_tenant_id': '123456',
    'service_password': 'foo',
    'service_username': 'adam',
    'service_protocol': 'http',
    'auth_protocol': 'http',
}

IDENTITY_SERVICE_RELATION_UNSET = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
}

IDENTITY_SERVICE_RELATION_HTTPS = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
    'service_protocol': 'https',
    'auth_protocol': 'https',
}

POSTGRESQL_DB_RELATION = {
    'host': 'dbserver.local',
    'user': 'adam',
    'password': 'foo',
}

POSTGRESQL_DB_CONFIG = {
    'database': 'foodb',
}

IDENTITY_SERVICE_RELATION = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
}

AMQP_RELATION = {
    'private-address': 'rabbithost',
    'password': 'foobar',
    'vip': '10.0.0.1',
}

AMQP_RELATION_WITH_SSL = {
    'private-address': 'rabbithost',
    'password': 'foobar',
    'vip': '10.0.0.1',
    'ssl_port': 5671,
    'ssl_ca': 'cert',
    'ha_queues': 'queues',
}

AMQP_AA_RELATION = {
    'amqp:0': {
        'rabbitmq/0': {
            'private-address': 'rabbithost1',
            'password': 'foobar',
        },
        'rabbitmq/1': {
            'private-address': 'rabbithost2',
        }
    }
}

AMQP_CONFIG = {
    'rabbit-user': 'adam',
    'rabbit-vhost': 'foo',
}

AMQP_NOVA_CONFIG = {
    'nova-rabbit-user': 'adam',
    'nova-rabbit-vhost': 'foo',
}

CEPH_RELATION = {
    'ceph:0': {
        'ceph/0': {
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
        },
        'ceph/1': {
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'false',
        },
    }
}

CEPH_RELATION_WITH_PUBLIC_ADDR = {
    'ceph:0': {
        'ceph/0': {
            'ceph-public-address': '192.168.1.10',
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar',
        },
        'ceph/1': {
            'ceph-public-address': '192.168.1.11',
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar',
        },
    }
}

SUB_CONFIG = """
nova:
    /etc/nova/nova.conf:
        sections:
            DEFAULT:
                - [nova-key1, value1]
                - [nova-key2, value2]
glance:
    /etc/glance/glance.conf:
        sections:
            DEFAULT:
                - [glance-key1, value1]
                - [glance-key2, value2]
"""

CINDER_SUB_CONFIG1 = """
cinder:
    /etc/cinder/cinder.conf:
        sections:
            cinder-1-section:
                - [key1, value1]
"""

CINDER_SUB_CONFIG2 = """
cinder:
    /etc/cinder/cinder.conf:
        sections:
            cinder-2-section:
                - [key2, value2]
        not-a-section:
            1234
"""

SUB_CONFIG_RELATION = {
    'nova-subordinate:0': {
        'nova-subordinate/0': {
            'private-address': 'nova_node1',
            'subordinate_configuration': json.dumps(yaml.load(SUB_CONFIG)),
        },
    },
    'glance-subordinate:0': {
        'glance-subordinate/0': {
            'private-address': 'glance_node1',
            'subordinate_configuration': json.dumps(yaml.load(SUB_CONFIG)),
        },
    },
    'foo-subordinate:0': {
        'foo-subordinate/0': {
            'private-address': 'foo_node1',
            'subordinate_configuration': 'ea8e09324jkadsfh',
        },
    },
    'cinder-subordinate:0': {
        'cinder-subordinate/0': {
            'private-address': 'cinder_node1',
            'subordinate_configuration': json.dumps(yaml.load(CINDER_SUB_CONFIG1)),
        },
    },
    'cinder-subordinate:1': {
        'cinder-subordinate/1': {
            'private-address': 'cinder_node1',
            'subordinate_configuration': json.dumps(yaml.load(CINDER_SUB_CONFIG2)),
        },
    },
}

# Imported in contexts.py and needs patching in setUp()
TO_PATCH = [
    'b64decode',
    'check_call',
    'get_cert',
    'get_ca_cert',
    'log',
    'config',
    'relation_get',
    'relation_ids',
    'related_units',
    'is_relation_made',
    'relation_set',
    'unit_get',
    'https',
    'determine_api_port',
    'determine_apache_port',
    'config',
    'is_clustered',
    'time',
    'https',
    'get_address_in_network',
    'local_unit',
    'get_ipv6_addr',
    'get_matchmaker_map',
]


class fake_config(object):

    def __init__(self, data):
        self.data = data

    def __call__(self, attr):
        if attr in self.data:
            return self.data[attr]
        return None


class ContextTests(unittest.TestCase):

    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        # mock at least a single relation + unit
        self.relation_ids.return_value = ['foo:0']
        self.related_units.return_value = ['foo/0']
        self.local_unit.return_value = 'localunit'

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.openstack.context.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_base_class_not_implemented(self):
        base = context.OSContextGenerator()
        self.assertRaises(NotImplementedError, base)

    def test_shared_db_context_with_data(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=SHARED_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.get_address_in_network.return_value = ''
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext()
        result = shared_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
            'database_type': 'mysql',
        }
        self.assertEquals(result, expected)

    def test_shared_db_context_with_data_and_access_net_mismatch(self):
        '''Mismatch between hostname and hostname for access net - defers execution'''
        relation = FakeRelation(relation_data=SHARED_DB_RELATION_ACCESS_NETWORK)
        self.relation_get.side_effect = relation.get
        self.get_address_in_network.return_value = '10.5.5.1'
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext()
        result = shared_db()
        self.assertEquals(result, {})
        self.relation_set.assert_called_with(relation_settings={'hostname': '10.5.5.1'})

    def test_shared_db_context_with_data_and_access_net_match(self):
        '''Correctly set hostname for access net returns complete context'''
        relation = FakeRelation(relation_data=SHARED_DB_RELATION_ACCESS_NETWORK)
        self.relation_get.side_effect = relation.get
        self.get_address_in_network.return_value = 'bar'
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext()
        result = shared_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
            'database_type': 'mysql',
        }
        self.assertEquals(result, expected)

    @patch('os.path.exists')
    @patch('__builtin__.open')
    def test_db_ssl(self, _open, osexists):
        osexists.return_value = False
        ssl_dir = '/etc/dbssl'
        db_ssl_ctxt = context.db_ssl(SHARED_DB_RELATION_SSL, {}, ssl_dir)
        expected = {
            'database_ssl_ca': ssl_dir + '/db-client.ca',
            'database_ssl_cert': ssl_dir + '/db-client.cert',
            'database_ssl_key': ssl_dir + '/db-client.key',
        }
        files = [
            call(expected['database_ssl_ca'], 'w'),
            call(expected['database_ssl_cert'], 'w'),
            call(expected['database_ssl_key'], 'w')
        ]
        for f in files:
            self.assertIn(f, _open.call_args_list)
        self.assertEquals(db_ssl_ctxt, expected)
        decode = [
            call(SHARED_DB_RELATION_SSL['ssl_ca']),
            call(SHARED_DB_RELATION_SSL['ssl_cert']),
            call(SHARED_DB_RELATION_SSL['ssl_key'])
        ]
        self.assertEquals(decode, self.b64decode.call_args_list)

    def test_db_ssl_nossldir(self):
        db_ssl_ctxt = context.db_ssl(SHARED_DB_RELATION_SSL, {}, None)
        self.assertEquals(db_ssl_ctxt, {})

    def test_shared_db_context_with_missing_relation(self):
        '''Test shared-db context missing relation data'''
        incomplete_relation = copy(SHARED_DB_RELATION)
        incomplete_relation['password'] = None
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        self.config.return_value = SHARED_DB_CONFIG
        shared_db = context.SharedDBContext()
        result = shared_db()
        self.assertEquals(result, {})

    def test_shared_db_context_with_missing_config(self):
        '''Test shared-db context missing relation data'''
        incomplete_config = copy(SHARED_DB_CONFIG)
        del incomplete_config['database-user']
        self.config.side_effect = fake_config(incomplete_config)
        relation = FakeRelation(relation_data=SHARED_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = incomplete_config
        shared_db = context.SharedDBContext()
        self.assertRaises(context.OSContextError, shared_db)

    def test_shared_db_context_with_params(self):
        '''Test shared-db context with object parameters'''
        shared_db = context.SharedDBContext(
            database='quantum', user='quantum', relation_prefix='quantum')
        relation = FakeRelation(relation_data=SHARED_DB_RELATION_NAMESPACED)
        self.relation_get.side_effect = relation.get
        result = shared_db()
        self.assertIn(
            call(rid='foo:0', unit='foo/0'),
            self.relation_get.call_args_list)
        self.assertEquals(
            result, {'database': 'quantum',
                     'database_user': 'quantum',
                     'database_password': 'bar2',
                     'database_host': 'bar',
                     'database_type': 'mysql'})

    def test_postgresql_db_context_with_data(self):
        '''Test postgresql-db context with all required data'''
        relation = FakeRelation(relation_data=POSTGRESQL_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.side_effect = fake_config(POSTGRESQL_DB_CONFIG)
        postgresql_db = context.PostgresqlDBContext()
        result = postgresql_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
            'database_type': 'postgresql',
        }
        self.assertEquals(result, expected)

    def test_postgresql_db_context_with_missing_relation(self):
        '''Test postgresql-db context missing relation data'''
        incomplete_relation = copy(POSTGRESQL_DB_RELATION)
        incomplete_relation['password'] = None
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        self.config.return_value = POSTGRESQL_DB_CONFIG
        postgresql_db = context.PostgresqlDBContext()
        result = postgresql_db()
        self.assertEquals(result, {})

    def test_postgresql_db_context_with_missing_config(self):
        '''Test postgresql-db context missing relation data'''
        incomplete_config = copy(POSTGRESQL_DB_CONFIG)
        del incomplete_config['database']
        self.config.side_effect = fake_config(incomplete_config)
        relation = FakeRelation(relation_data=POSTGRESQL_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = incomplete_config
        postgresql_db = context.PostgresqlDBContext()
        self.assertRaises(context.OSContextError, postgresql_db)

    def test_postgresql_db_context_with_params(self):
        '''Test postgresql-db context with object parameters'''
        postgresql_db = context.PostgresqlDBContext(database='quantum')
        result = postgresql_db()
        self.assertEquals(result['database'], 'quantum')

    def test_identity_service_context_with_data(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_UNSET)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_data_http(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_HTTP)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': '123456',
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_data_https(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_HTTPS)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'https',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'https'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_missing_relation(self):
        '''Test shared-db context missing relation data'''
        incomplete_relation = copy(IDENTITY_SERVICE_RELATION_UNSET)
        incomplete_relation['service_password'] = None
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        self.assertEquals(result, {})

    def test_amqp_context_with_data(self):
        '''Test amqp context with all required data'''
        relation = FakeRelation(relation_data=AMQP_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo'
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_data_altname(self):
        '''Test amqp context with alternative relation name'''
        relation = FakeRelation(relation_data=AMQP_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_NOVA_CONFIG
        amqp = context.AMQPContext(
            rel_name='amqp-nova',
            relation_prefix='nova')
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo'
        }
        self.assertEquals(result, expected)

    @patch('__builtin__.open')
    def test_amqp_context_with_data_ssl(self, _open):
        '''Test amqp context with all required data and ssl'''
        relation = FakeRelation(relation_data=AMQP_RELATION_WITH_SSL)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        ssl_dir = '/etc/sslamqp'
        amqp = context.AMQPContext(ssl_dir=ssl_dir)
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbit_ssl_port': 5671,
            'rabbitmq_virtual_host': 'foo',
            'rabbit_ssl_ca': ssl_dir + '/rabbit-client-ca.pem',
            'rabbitmq_ha_queues': True,
        }
        _open.assert_called_once_with(ssl_dir + '/rabbit-client-ca.pem', 'w')
        self.assertEquals(result, expected)
        self.assertEquals([call(AMQP_RELATION_WITH_SSL['ssl_ca'])],
                          self.b64decode.call_args_list)

    def test_amqp_context_with_data_ssl_noca(self):
        '''Test amqp context with all required data with ssl but missing ca'''
        relation = FakeRelation(relation_data=AMQP_RELATION_WITH_SSL)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbit_ssl_port': 5671,
            'rabbitmq_virtual_host': 'foo',
            'rabbit_ssl_ca': 'cert',
            'rabbitmq_ha_queues': True,
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_data_clustered(self):
        '''Test amqp context with all required data with clustered rabbit'''
        relation_data = copy(AMQP_RELATION)
        relation_data['clustered'] = 'yes'
        relation = FakeRelation(relation_data=relation_data)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'clustered': True,
            'rabbitmq_host': relation_data['vip'],
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_data_active_active(self):
        '''Test amqp context with required data with active/active rabbit'''
        relation_data = copy(AMQP_AA_RELATION)
        relation = FakeRelation(relation_data=relation_data)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost1',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
            'rabbitmq_hosts': 'rabbithost2,rabbithost1',
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_missing_relation(self):
        '''Test amqp context missing relation data'''
        incomplete_relation = copy(AMQP_RELATION)
        incomplete_relation['password'] = ''
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        self.assertEquals({}, result)

    def test_amqp_context_with_missing_config(self):
        '''Test amqp context missing relation data'''
        incomplete_config = copy(AMQP_CONFIG)
        del incomplete_config['rabbit-user']
        relation = FakeRelation(relation_data=AMQP_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = incomplete_config
        amqp = context.AMQPContext()
        self.assertRaises(context.OSContextError, amqp)

    def test_ceph_no_relids(self):
        '''Test empty ceph realtion'''
        relation = FakeRelation(relation_data={})
        self.relation_ids.side_effect = relation.get
        ceph = context.CephContext()
        result = ceph()
        self.assertEquals(result, {})

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_data(self, ensure_packages, mkdir, isdir,
                                    config):
        '''Test ceph context with all relation data'''
        config.return_value = True
        isdir.return_value = False
        relation = FakeRelation(relation_data=CEPH_RELATION)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': 'ceph_node2 ceph_node1',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true'
        }
        self.assertEquals(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_missing_data(self, ensure_packages, mkdir):
        '''Test ceph context with missing relation data'''
        relation = copy(CEPH_RELATION)
        for k, v in relation.iteritems():
            for u in v.iterkeys():
                del relation[k][u]['auth']
        relation = FakeRelation(relation_data=relation)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        self.assertEquals(result, {})
        self.assertFalse(ensure_packages.called)

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_public_addr(
            self, ensure_packages, mkdir, isdir, config):
        '''Test ceph context in host with multiple networks with all
        relation data'''
        isdir.return_value = False
        config.return_value = True
        relation = FakeRelation(relation_data=CEPH_RELATION_WITH_PUBLIC_ADDR)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': '192.168.1.11 192.168.1.10',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
        }
        self.assertEquals(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_missing_public_addr(
            self, ensure_packages, mkdir, isdir, config):
        '''Test ceph context in host with multiple networks with no
        ceph-public-addr in relation data'''
        isdir.return_value = False
        config.return_value = True
        relation = deepcopy(CEPH_RELATION_WITH_PUBLIC_ADDR)
        del relation['ceph:0']['ceph/0']['ceph-public-address']
        relation = FakeRelation(relation_data=relation)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()

        result = ceph()
        expected = {
            'mon_hosts': '192.168.1.11 ceph_node1',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
        }
        self.assertEquals(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_data(self, local_unit, unit_get):
        '''Test haproxy context with all relation data'''
        cluster_relation = {
            'cluster:0': {
                'peer/1': {
                    'private-address': 'cluster-peer1.localnet',
                },
                'peer/2': {
                    'private-address': 'cluster-peer2.localnet',
                },
            },
        }
        local_unit.return_value = 'peer/0'
        unit_get.return_value = 'cluster-peer0.localnet'
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.get_address_in_network.return_value = 'cluster-peer0.localnet'
        self.config.return_value = False
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'units': {
                'peer-0': 'cluster-peer0.localnet',
                'peer-1': 'cluster-peer1.localnet',
                'peer-2': 'cluster-peer2.localnet',
            },

            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'stat_port': ':8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    @patch('charmhelpers.contrib.openstack.context.get_ipv6_addr')
    def test_haproxy_context_with_data_ipv6(
            self, local_unit, unit_get, get_ipv6_addr):
        '''Test haproxy context with all relation data'''
        cluster_relation = {
            'cluster:0': {
                'peer/1': {
                    'private-address': 'cluster-peer1.localnet',
                },
                'peer/2': {
                    'private-address': 'cluster-peer2.localnet',
                },
            },
        }

        unit_get.return_value = 'peer/0'
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.get_address_in_network.return_value = 'cluster-peer0.localnet'
        self.get_ipv6_addr.return_value = 'cluster-peer0.localnet'
        self.config.side_effect = [True, None, True]
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'units': {
                'peer-0': 'cluster-peer0.localnet',
                'peer-1': 'cluster-peer1.localnet',
                'peer-2': 'cluster-peer2.localnet'
            },

            'local_host': 'ip6-localhost',
            'haproxy_host': '::',
            'stat_port': ':::8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])

    def test_haproxy_context_with_missing_data(self):
        '''Test haproxy context with missing relation data'''
        self.relation_ids.return_value = []
        haproxy = context.HAProxyContext()
        self.assertEquals({}, haproxy())

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_no_peers(self, local_unit, unit_get):
        '''Test haproxy context with single unit'''
        # peer relations always show at least one peer relation, even
        # if unit is alone. should be an incomplete context.
        cluster_relation = {
            'cluster:0': {
                'peer/0': {
                    'private-address': 'lonely.clusterpeer.howsad',
                },
            },
        }
        local_unit.return_value = 'peer/0'
        unit_get.return_value = 'lonely.clusterpeer.howsad'
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.config.return_value = False
        haproxy = context.HAProxyContext()
        self.assertEquals({}, haproxy())

    def test_https_context_with_no_https(self):
        '''Test apache2 https when no https data available'''
        apache = context.ApacheSSLContext()
        self.https.return_value = False
        self.assertEquals({}, apache())

    def _test_https_context(self, apache, is_clustered, peer_units):
        self.https.return_value = True

        if is_clustered:
            self.determine_api_port.return_value = 8756
            self.determine_apache_port.return_value = 8766
        else:
            self.determine_api_port.return_value = 8766
            self.determine_apache_port.return_value = 8776

        config = {'vip': 'cinderhost1vip'}
        self.config.side_effect = lambda key: config[key]
        self.unit_get.return_value = 'cinderhost1'
        self.is_clustered.return_value = is_clustered
        apache = context.ApacheSSLContext()
        apache.configure_cert = MagicMock
        apache.enable_modules = MagicMock
        apache.external_ports = '8776'
        apache.service_namespace = 'cinder'

        if is_clustered:
            ex = {
                'private_address': 'cinderhost1vip',
                'namespace': 'cinder',
                'endpoints': [(8766, 8756)],
            }
        else:
            ex = {
                'private_address': 'cinderhost1',
                'namespace': 'cinder',
                'endpoints': [(8776, 8766)],
            }

        self.assertEquals(ex, apache())
        self.assertTrue(apache.configure_cert.called)
        self.assertTrue(apache.enable_modules.called)

    def test_https_context_no_peers_no_cluster(self):
        '''Test apache2 https on a single, unclustered unit'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=None)

    def test_https_context_wth_peers_no_cluster(self):
        '''Test apache2 https on a unclustered unit with peers'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=[1, 2])

    def test_https_context_wth_peers_cluster(self):
        '''Test apache2 https on a clustered unit with peers'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=True, peer_units=[1, 2])

    def test_https_context_loads_correct_apache_mods(self):
        '''Test apache2 context also loads required apache modules'''
        apache = context.ApacheSSLContext()
        apache.enable_modules()
        ex_cmd = ['a2enmod', 'ssl', 'proxy', 'proxy_http']
        self.check_call.assert_called_with(ex_cmd)

    @patch('__builtin__.open')
    @patch('os.mkdir')
    @patch('os.path.isdir')
    def test_https_configure_cert(self, isdir, mkdir, _open):
        '''Test apache2 properly installs certs and keys to disk'''
        isdir.return_value = False
        self.get_cert.return_value = ('SSL_CERT', 'SSL_KEY')
        self.get_ca_cert.return_value = 'CA_CERT'
        apache = context.ApacheSSLContext()
        apache.service_namespace = 'cinder'
        apache.configure_cert()
        # appropriate directories are created.
        dirs = [call('/etc/apache2/ssl'), call('/etc/apache2/ssl/cinder')]
        self.assertEquals(dirs, mkdir.call_args_list)
        # appropriate files are opened for writing.
        _ca = '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt'
        files = [call('/etc/apache2/ssl/cinder/cert', 'w'),
                 call('/etc/apache2/ssl/cinder/key', 'w'),
                 call(_ca, 'w')]
        for f in files:
            self.assertIn(f, _open.call_args_list)
        # appropriate bits are b64decoded.
        decode = [call('SSL_CERT'), call('SSL_KEY'), call('CA_CERT')]
        self.assertEquals(decode, self.b64decode.call_args_list)

    def test_image_service_context_missing_data(self):
        '''Test image-service with missing relation and missing data'''
        image_service = context.ImageServiceContext()
        self.relation_ids.return_value = []
        self.assertEquals({}, image_service())
        self.relation_ids.return_value = ['image-service:0']
        self.related_units.return_value = ['glance/0']
        self.relation_get.return_value = None
        self.assertEquals({}, image_service())

    def test_image_service_context_with_data(self):
        '''Test image-service with required data'''
        image_service = context.ImageServiceContext()
        self.relation_ids.return_value = ['image-service:0']
        self.related_units.return_value = ['glance/0']
        self.relation_get.return_value = 'http://glancehost:9292'
        self.assertEquals({'glance_api_servers': 'http://glancehost:9292'},
                          image_service())

    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_context_base_properties(self, attr):
        '''Test neutron context base properties'''
        neutron = context.NeutronContext()
        attr.return_value = 'quantum-plugin-package'
        self.assertEquals(None, neutron.plugin)
        self.assertEquals(None, neutron.network_manager)
        self.assertEquals(None, neutron.neutron_security_groups)
        self.assertEquals('quantum-plugin-package', neutron.packages)

    @patch.object(context, 'neutron_plugin_attribute')
    @patch.object(context, 'apt_install')
    @patch.object(context, 'filter_installed_packages')
    def test_neutron_ensure_package(self, _filter, _install, _packages):
        '''Test neutron context installed required packages'''
        _filter.return_value = ['quantum-plugin-package']
        _packages.return_value = [['quantum-plugin-package']]
        neutron = context.NeutronContext()
        neutron._ensure_packages()
        _install.assert_called_with(['quantum-plugin-package'], fatal=True)

    @patch.object(context.NeutronContext, 'network_manager')
    @patch.object(context.NeutronContext, 'plugin')
    def test_neutron_save_flag_file(self, plugin, nm):
        neutron = context.NeutronContext()
        plugin.__get__ = MagicMock(return_value='ovs')
        nm.__get__ = MagicMock(return_value='quantum')
        with patch_open() as (_o, _f):
            neutron._save_flag_file()
            _o.assert_called_with('/etc/nova/quantum_plugin.conf', 'wb')
            _f.write.assert_called_with('ovs\n')

        nm.__get__ = MagicMock(return_value='neutron')
        with patch_open() as (_o, _f):
            neutron._save_flag_file()
            _o.assert_called_with('/etc/nova/neutron_plugin.conf', 'wb')
            _f.write.assert_called_with('ovs\n')

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_ovs_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'ovs',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.ovs_ctxt())

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_nvp_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'nvp',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.nvp_ctxt())

    @patch.object(context, 'config')
    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_n1kv_plugin_context(self, attr, ip, sec_groups, config):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        config.return_value = 'n1kv'
        neutron = context.NeutronContext()
        self.assertEquals({
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'n1kv',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1',
            'config': 'some.quantum.driver.class',
            'vsm_ip': 'n1kv',
            'vsm_username': 'n1kv',
            'vsm_password': 'n1kv',
            'restrict_policy_profiles': 'n1kv',
        }, neutron.n1kv_ctxt())

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_neutron_ctxt(self, mock_network_manager,
                                  mock_unit_get):
        vip = '88.11.22.33'
        priv_addr = '10.0.0.1'
        mock_unit_get.return_value = priv_addr
        neutron = context.NeutronContext()

        config = {'vip': vip}
        self.config.side_effect = lambda key: config[key]
        mock_network_manager.__get__ = Mock(return_value='neutron')

        self.is_clustered.return_value = False
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'https://%s:9696' % (priv_addr)},
            neutron.neutron_ctxt()
        )

        self.is_clustered.return_value = True
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'https://%s:9696' % (vip)},
            neutron.neutron_ctxt()
        )

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_neutron_ctxt_http(self, mock_network_manager,
                                       mock_unit_get):
        vip = '88.11.22.33'
        priv_addr = '10.0.0.1'
        mock_unit_get.return_value = priv_addr
        neutron = context.NeutronContext()

        config = {'vip': vip}
        self.config.side_effect = lambda key: config[key]
        self.https.return_value = False
        mock_network_manager.__get__ = Mock(return_value='neutron')

        self.is_clustered.return_value = False
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'http://%s:9696' % (priv_addr)},
            neutron.neutron_ctxt()
        )

        self.is_clustered.return_value = True
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'http://%s:9696' % (vip)},
            neutron.neutron_ctxt()
        )

    @patch.object(context.NeutronContext, 'neutron_ctxt')
    @patch.object(context.NeutronContext, '_save_flag_file')
    @patch.object(context.NeutronContext, 'ovs_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_generation(self, mock_network_manager,
                                             mock_ensure_packages,
                                             mock_plugin, mock_ovs_ctxt,
                                             mock_save_flag_file,
                                             mock_neutron_ctxt):

        mock_neutron_ctxt.return_value = {'network_manager': 'neutron',
                                          'neutron_url': 'https://foo:9696'}
        config = {'neutron-alchemy-flags': None}
        self.config.side_effect = lambda key: config[key]
        neutron = context.NeutronContext()

        mock_network_manager.__get__ = Mock(return_value='flatdhcpmanager')
        mock_plugin.__get__ = Mock()

        self.assertEquals({}, neutron())
        self.assertTrue(mock_network_manager.__get__.called)
        self.assertFalse(mock_plugin.__get__.called)

        mock_network_manager.__get__.return_value = 'neutron'
        mock_plugin.__get__ = Mock(return_value=None)
        self.assertEquals({}, neutron())
        self.assertTrue(mock_plugin.__get__.called)

        mock_ovs_ctxt.return_value = {'ovs': 'ovs_context'}
        mock_plugin.__get__.return_value = 'ovs'
        self.assertEquals(
            {'network_manager': 'neutron',
             'ovs': 'ovs_context',
             'neutron_url': 'https://foo:9696'},
            neutron()
        )

    @patch.object(context.NeutronContext, 'neutron_ctxt')
    @patch.object(context.NeutronContext, '_save_flag_file')
    @patch.object(context.NeutronContext, 'nvp_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_gen_nvp_and_alchemy(self,
                                                      mock_network_manager,
                                                      mock_ensure_packages,
                                                      mock_plugin,
                                                      mock_nvp_ctxt,
                                                      mock_save_flag_file,
                                                      mock_neutron_ctxt):

        mock_neutron_ctxt.return_value = {'network_manager': 'neutron',
                                          'neutron_url': 'https://foo:9696'}
        config = {'neutron-alchemy-flags': 'pool_size=20'}
        self.config.side_effect = lambda key: config[key]
        neutron = context.NeutronContext()

        mock_network_manager.__get__ = Mock(return_value='flatdhcpmanager')
        mock_plugin.__get__ = Mock()

        self.assertEquals({}, neutron())
        self.assertTrue(mock_network_manager.__get__.called)
        self.assertFalse(mock_plugin.__get__.called)

        mock_network_manager.__get__.return_value = 'neutron'
        mock_plugin.__get__ = Mock(return_value=None)
        self.assertEquals({}, neutron())
        self.assertTrue(mock_plugin.__get__.called)

        mock_nvp_ctxt.return_value = {'nvp': 'nvp_context'}
        mock_plugin.__get__.return_value = 'nvp'
        self.assertEquals(
            {'network_manager': 'neutron',
             'nvp': 'nvp_context',
             'neutron_alchemy_flags': {'pool_size': '20'},
             'neutron_url': 'https://foo:9696'},
            neutron()
        )

    @patch.object(context, 'config')
    def test_os_configflag_context(self, config):
        flags = context.OSConfigFlagContext()

        # single
        config.return_value = 'deadbeef=True'
        self.assertEquals({
            'user_config_flags': {
                'deadbeef': 'True',
            }
        }, flags())

        # multi
        config.return_value = 'floating_ip=True,use_virtio=False,max=5'
        self.assertEquals({
            'user_config_flags': {
                'floating_ip': 'True',
                'use_virtio': 'False',
                'max': '5',
            }
        }, flags())

        for empty in [None, '']:
            config.return_value = empty
            self.assertEquals({}, flags())

        # multi with commas
        config.return_value = 'good_flag=woot,badflag,great_flag=w00t'
        self.assertEquals({
            'user_config_flags': {
                'good_flag': 'woot,badflag',
                'great_flag': 'w00t',
            }
        }, flags())

        # missing key
        config.return_value = 'good_flag=woot=toow'
        self.assertRaises(context.OSContextError, flags)

        # bad value
        config.return_value = 'good_flag=woot=='
        self.assertRaises(context.OSContextError, flags)

    def test_os_subordinate_config_context(self):
        relation = FakeRelation(relation_data=SUB_CONFIG_RELATION)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        nova_sub_ctxt = context.SubordinateConfigContext(
            service='nova',
            config_file='/etc/nova/nova.conf',
            interface='nova-subordinate',
        )
        glance_sub_ctxt = context.SubordinateConfigContext(
            service='glance',
            config_file='/etc/glance/glance.conf',
            interface='glance-subordinate',
        )
        cinder_sub_ctxt = context.SubordinateConfigContext(
            service='cinder',
            config_file='/etc/cinder/cinder.conf',
            interface='cinder-subordinate',
        )
        foo_sub_ctxt = context.SubordinateConfigContext(
            service='foo',
            config_file='/etc/foo/foo.conf',
            interface='foo-subordinate',
        )
        self.assertEquals(
            nova_sub_ctxt(),
            {'sections': {
                'DEFAULT': [
                    ['nova-key1', 'value1'],
                    ['nova-key2', 'value2']]
            }}
        )
        self.assertEquals(
            glance_sub_ctxt(),
            {'sections': {
                'DEFAULT': [
                    ['glance-key1', 'value1'],
                    ['glance-key2', 'value2']]
            }}
        )
        self.assertEquals(
            cinder_sub_ctxt(),
            {'sections': {
                'cinder-1-section': [
                    ['key1', 'value1']],
                'cinder-2-section': [
                    ['key2', 'value2']]

            }, 'not-a-section': 1234}
        )

        # subrodinate supplies nothing for given config
        glance_sub_ctxt.config_file = '/etc/glance/glance-api-paste.ini'
        self.assertEquals(glance_sub_ctxt(), {'sections': {}})

        # subordinate supplies bad input
        self.assertEquals(foo_sub_ctxt(), {'sections': {}})

    def test_syslog_context(self):
        self.config.side_effect = fake_config({'use-syslog': 'foo'})
        syslog = context.SyslogContext()
        result = syslog()
        expected = {
            'use_syslog': 'foo',
        }
        self.assertEquals(result, expected)

    def test_loglevel_context_set(self):
        self.config.side_effect = fake_config({
            'debug': True,
            'verbose': True,
        })
        syslog = context.LogLevelContext()
        result = syslog()
        expected = {
            'debug': True,
            'verbose': True,
        }
        self.assertEquals(result, expected)

    def test_loglevel_context_unset(self):
        self.config.side_effect = fake_config({
            'debug': None,
            'verbose': None,
        })
        syslog = context.LogLevelContext()
        result = syslog()
        expected = {
            'debug': False,
            'verbose': False,
        }
        self.assertEquals(result, expected)

    def test_zeromq_context_unrelated(self):
        self.is_relation_made.return_value = False
        self.assertEquals(context.ZeroMQContext()(), {})

    def test_zeromq_context_related(self):
        self.is_relation_made.return_value = True
        self.relation_ids.return_value = ['zeromq-configuration:1']
        self.related_units.return_value = ['openstack-zeromq/0']
        self.relation_get.side_effect = ['nonce-data', 'hostname']
        self.assertEquals(context.ZeroMQContext()(),
                          {'zmq_host': 'hostname',
                           'zmq_nonce': 'nonce-data'})

    def test_notificationdriver_context_nozmq(self):
        self.is_relation_made.return_value = False
        self.assertEquals(context.NotificationDriverContext()(), {'notifications': True})

    def test_notificationdriver_context_zmq_nometer(self):
        self.is_relation_made.return_value = True
        self.get_matchmaker_map.return_value = {
            'cinder-scheduler': ['juju-t-machine-4'],
        }
        self.assertEquals(context.NotificationDriverContext()(),
                          {'notifications': False})

    def test_notificationdriver_context_zmq_meter(self):
        self.is_relation_made.return_value = True
        self.get_matchmaker_map.return_value = {
            'metering-agent': ['juju-t-machine-4'],
        }
        self.assertEquals(context.NotificationDriverContext()(),
                          {'notifications': True})
