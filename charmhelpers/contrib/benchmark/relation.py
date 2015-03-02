# Copyright 2014-2015 Canonical Limited.
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

import subprocess
import time
import os
from distutils.spawn import find_executable
from charmhelpers.core import hookenv


def action_set(key, val):
    if find_executable('action-set'):
        action_cmd = ['action-set']
        if isinstance(val, dict):
            for k, v in val.iteritems():
                action_set('%s.%s' % (key, k), v)
            return

        action_cmd.append('%s=%s' % (key, val))
        subprocess.check_call(action_cmd)
        return True
    return False


class Benchmark():
    """
    Helper class for the `benchmark` interface.

    :param list actions: Define the actions that are also benchmarks

    From inside the benchmark-relation-changed hook, you would
    Benchmark(['memory', 'cpu', 'disk', 'smoke', 'custom'])

    """

    required_keys = [
        'hostname',
        'port',
        'graphite_port',
        'graphite_endpoint',
        'api_port'
    ]

    def __init__(self, benchmarks=None):
        if benchmarks is not None:
            for rid in sorted(hookenv.relation_ids('benchmark')):
                hookenv.relation_set(relation_id=rid, relation_settings={
                    'benchmarks': ",".join(benchmarks)
                })

        # Check the relation data
        config = {}
        for key in self.required_keys:
            val = hookenv.relation_get(key)
            if val is not None:
                config[key] = val
            else:
                # We don't have all of the required keys
                config = {}
                break

        if len(config):
            f = open('/etc/benchmark.conf', 'w')
            for key, val in config.iteritems():
                f.write("%s=%s\n" % (key, val))
            f.close()

    def start(self):
        action_set('meta.start', time.strftime('%Y-%m-%dT%H:%M:%SZ'))

        """
        If the collectd charm is also installed, tell it to send a snapshot
        of the current profile data.
        """
        COLLECT_PROFILE_DATA = '/usr/local/bin/collect-profile-data'
        if os.path.exists(COLLECT_PROFILE_DATA):
            subprocess.check_output([COLLECT_PROFILE_DATA])

    def finish(self):
        action_set('meta.stop', time.strftime('%Y-%m-%dT%H:%M:%SZ'))
