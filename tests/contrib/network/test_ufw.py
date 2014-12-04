from __future__ import print_function
__author__ = 'Felipe Reyes <felipe.reyes@canonical.com>'

import mock
import subprocess
import unittest

from charmhelpers.contrib.network import ufw


class TestUFW(unittest.TestCase):
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_enable_ok(self, check_output, log):
        msg = 'Firewall is active and enabled on system startup\n'
        check_output.return_value = msg
        self.assertTrue(ufw.enable())

        check_output.assert_any_call(['ufw', 'enable'], env={'LANG': 'en_US'})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call('ufw enabled', level='INFO')

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_enable_fail(self, check_output, log):
        msg = 'neneene\n'
        check_output.return_value = msg
        self.assertFalse(ufw.enable())

        check_output.assert_any_call(['ufw', 'enable'], env={'LANG': 'en_US'})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call("ufw couldn't be enabled", level='WARN')

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_disable_ok(self, check_output, log):
        msg = 'Firewall stopped and disabled on system startup\n'
        check_output.return_value = msg
        self.assertTrue(ufw.disable())

        check_output.assert_any_call(['ufw', 'disable'], env={'LANG': 'en_US'})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call('ufw disabled', level='INFO')

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_disable_fail(self, check_output, log):
        msg = 'neneene\n'
        check_output.return_value = msg
        self.assertFalse(ufw.disable())

        check_output.assert_any_call(['ufw', 'disable'], env={'LANG': 'en_US'})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call("ufw couldn't be disabled", level='WARN')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_modify_access_ufw_is_disabled(self, check_output, log,
                                           is_enabled):
        is_enabled.return_value = False
        ufw.modify_access('127.0.0.1')
        log.assert_any_call('ufw is disabled, skipping modify_access()',
                            level='WARN')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               'any'], stdout=subprocess.PIPE)
        log.assert_any_call('ufw allow: ufw allow from 127.0.0.1 to any',
                            level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow_set_proto(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1', proto='udp')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               'any', 'proto', 'udp'], stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to any proto udp'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow_set_port(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               'any', 'port', '80'], stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to any port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow_set_dst(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1', dst='127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_grant_access(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.grant_access('127.0.0.1', dst='127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_revoke_access(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.revoke_access('127.0.0.1', dst='127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'delete', 'allow', 'from', '127.0.0.1',
                               'to', '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw delete: ufw delete allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('subprocess.check_output')
    def test_service_open(self, check_output):
        ufw.service('ssh', 'open')
        check_output.assert_any_call(['ufw', 'allow', 'ssh'])

    @mock.patch('subprocess.check_output')
    def test_service_close(self, check_output):
        ufw.service('ssh', 'close')
        check_output.assert_any_call(['ufw', 'delete', 'allow', 'ssh'])

    @mock.patch('subprocess.check_output')
    def test_service_unsupport_action(self, check_output):
        self.assertRaises(Exception, ufw.service, 'ssh', 'nenene')
