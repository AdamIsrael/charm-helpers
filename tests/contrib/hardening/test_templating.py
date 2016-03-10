# Copyright 2016 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import tempfile
import os

from mock import patch, MagicMock
from unittest import TestCase

os.environ['JUJU_CHARM_DIR'] = '/tmp'

from charmhelpers.contrib.hardening import templating
from charmhelpers.contrib.hardening import utils
from charmhelpers.contrib.hardening.audits.file import (
    TemplatedFile,
    FileContentAudit,
)
from charmhelpers.contrib.hardening.ssh.checks import (
    config as ssh_config_check
)
from charmhelpers.contrib.hardening.host.checks import (
    sysctl,
    securetty,
)
from charmhelpers.contrib.hardening.apache.checks import (
    config as apache_config_check
)
from charmhelpers.contrib.hardening.mysql.checks import (
    config as mysql_config_check
)


class TemplatingTestCase(TestCase):

    def setUp(self):
        super(TemplatingTestCase, self).setUp()
        self.pathindex = {}

    def get_renderers(self, audits):
        renderers = []
        for a in audits:
            if issubclass(a.__class__, TemplatedFile):
                renderers.append(a)

        return renderers

    def get_contentcheckers(self, audits):
        contentcheckers = []
        for a in audits:
            if issubclass(a.__class__, FileContentAudit):
                contentcheckers.append(a)

        return contentcheckers

    def render(self, renderers):
        for template in renderers:
            with patch.object(template, 'pre_write', lambda: None):
                with patch.object(template, 'post_write', lambda: None):
                    with patch.object(template, 'run_service_actions'):
                        with patch.object(template, 'save_checksum'):
                            for p in template.paths:
                                template.comply(p)

    def checkcontents(self, contentcheckers):
        for check in contentcheckers:
            if check.path not in self.pathindex:
                continue

            self.assertTrue(check.is_compliant(self.pathindex[check.path]))

    @patch.object(ssh_config_check, 'lsb_release',
                  lambda: {'DISTRIB_CODENAME': 'precise'})
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    @patch.object(ssh_config_check, 'log', lambda *args, **kwargs: None)
    def test_ssh_config_render_and_check_lt_trusty(self, mock_write,
                                                   mock_ensure_permissions):
        audits = ssh_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            with tempfile.NamedTemporaryFile(delete=False) as FTMP:
                if path in self.pathindex:
                    raise Exception("File already rendered '%s'" % path)

                self.pathindex[path] = FTMP.name
                with open(FTMP.name, 'w') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/ssh/ssh_config', args_list[0][0][0])
        self.assertEqual('/etc/ssh/sshd_config', args_list[1][0][0])
        self.assertEqual(mock_write.call_count, 2)

    @patch.object(ssh_config_check, 'lsb_release',
                  lambda: {'DISTRIB_CODENAME': 'trusty'})
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    @patch.object(ssh_config_check, 'log', lambda *args, **kwargs: None)
    def test_ssh_config_render_and_check_gte_trusty(self, mock_write,
                                                    mock_ensure_permissions):
        audits = ssh_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            with tempfile.NamedTemporaryFile(delete=False) as FTMP:
                if path in self.pathindex:
                    raise Exception("File already rendered '%s'" % path)

                self.pathindex[path] = FTMP.name
                with open(FTMP.name, 'w') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/ssh/ssh_config', args_list[0][0][0])
        self.assertEqual('/etc/ssh/sshd_config', args_list[1][0][0])
        self.assertEqual(mock_write.call_count, 2)

    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_os_sysctl_and_check(self, mock_write, mock_ensure_permissions):
        audits = sysctl.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as FTMP:
                self.pathindex[path] = FTMP.name
                with open(FTMP.name, 'w') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/sysctl.conf', args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 1)

    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_os_securetty_and_check(self, mock_write, mock_ensure_permissions):
        audits = securetty.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as FTMP:
                self.pathindex[path] = FTMP.name
                with open(FTMP.name, 'w') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/securetty', args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 1)

    
    @patch.object(apache_config_check.utils, 'get_settings', lambda x: {
        'common': {'apache_dir': '/tmp/foo'},
        'hardening': {
            'allowed_http_methods': {'GOGETEM'},
            'modules_to_disable': {'modfoo'},
            'traceenable': 'off'
        }
    })
    @patch('charmhelpers.contrib.hardening.audits.file.os.path.exists',
           lambda *a, **kwa: True)
    @patch.object(apache_config_check, 'subprocess')
    @patch.object(apache_config_check, 're')
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_apache_conf_and_check(self, mock_write, mock_ensure_permissions,
                                   mock_re, mock_subprocess):
        mock_group = MagicMock()
        mock_group.side_effect = "foo" 
        mock_re.search.return_value = mock_group
        mock_subprocess.call.return_value = 0
        audits = apache_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as FTMP:
                self.pathindex[path] = FTMP.name
                with open(FTMP.name, 'w') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/tmp/foo/mods-available/alias.conf',
                         args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 2)

    @patch.object(apache_config_check.utils, 'get_settings', lambda x: {
        'security': {},
        'hardening': {
            'mysql-conf': '/tmp/foo/mysql.cnf',
            'hardening-conf': '/tmp/foo/conf.d/hardening.cnf'
        }
    })
    @patch('charmhelpers.contrib.hardening.audits.file.os.path.exists',
           lambda *a, **kwa: True)
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    #@patch.object(templating, 'log', lambda *args, **kwargs: None)
    #@patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_mysql_conf_and_check(self, mock_write, mock_ensure_permissions):
        audits = mysql_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as FTMP:
                self.pathindex[path] = FTMP.name
                with open(FTMP.name, 'w') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/tmp/foo/conf.d/hardening.cnf',
                         args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 1)

    def tearDown(self):
        # Cleanup
        for path in self.pathindex.itervalues():
            os.remove(path)

        super(TemplatingTestCase, self).tearDown()
