
import unittest

from mock import patch
from copy import copy

import charmhelpers.contrib.openstack.context as context


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

    def get(self, attr=None, unit=None, rid=None):
        if not rid or rid == 'foo:0':
            if attr is None:
                return self.relation_data
            elif attr in self.relation_data:
                return self.relation_data[attr]
            return None
        else:
            if rid not in self.relation_data:
                return None
            try:
                relation = self.relation_data[rid][unit]
            except KeyError:
                return None
            if attr in relation:
                return relation[attr]
            return None

    def relation_ids(self, relation):
        return self.relation_data.keys()

    def relation_units(self, relation_id):
        if relation_id not in self.relation_data:
            return None
        return self.relation_data[relation_id].keys()

SHARED_DB_RELATION = {
    'db_host': 'dbserver.local',
    'password': 'foo',
}

SHARED_DB_CONFIG = {
    'database-user': 'adam',
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

AMQP_CONFIG = {
    'rabbit-user': 'adam',
    'rabbit-vhost': 'foo',
}

CEPH_RELATION = {
    'ceph:0': {
        'ceph/0': {
            'private-address': 'ceph_node1',
            'auth': 'foo',
        },
        'ceph/1': {
            'private-address': 'ceph_node2',
            'auth': 'foo',
        },
    }
}


# Imported in contexts.py and needs patching in setUp()
TO_PATCH = [
    'log',
    'config',
    'relation_get',
    'relation_ids',
    'related_units',
]


class ContextTests(unittest.TestCase):
    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        # mock at least a single relation + unit
        self.relation_ids.return_value = ['foo:0']
        self.related_units.return_value = ['foo/0']

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.openstack.context.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_shared_db_context_with_data(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=SHARED_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = SHARED_DB_CONFIG
        shared_db = context.SharedDBContext()
        result = shared_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
        }
        self.assertEquals(result, expected)

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
        relation = FakeRelation(relation_data=SHARED_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = incomplete_config
        shared_db = context.SharedDBContext()
        self.assertRaises(context.OSContextError, shared_db)

    def test_identity_service_context_with_data(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_missing_relation(self):
        '''Test shared-db context missing relation data'''
        incomplete_relation = copy(IDENTITY_SERVICE_RELATION)
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
            'rabbitmq_host': relation_data['vip'],
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo'
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

    def test_ceph_context_with_data(self):
        '''Test ceph context with all relation data'''
        relation = FakeRelation(relation_data=CEPH_RELATION)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': 'ceph_node2 ceph_node1',
            'auth': 'foo'
        }
        self.assertEquals(result, expected)

    def test_ceph_context_with_missing_data(self):
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
