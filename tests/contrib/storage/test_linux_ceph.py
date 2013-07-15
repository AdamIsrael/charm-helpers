from mock import patch, call
from testtools import TestCase
import json

import charmhelpers.contrib.storage.linux.ceph as ceph_utils
from subprocess import CalledProcessError
from tests.helpers import patch_open


LS_POOLS = """
images
volumes
rbd
"""

LS_RBDS = """
rbd1
rbd2
rbd3
"""

IMG_MAP = """
bar
baz
"""


class CephUtilsTests(TestCase):
    def setUp(self):
        super(CephUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'check_call',
            'check_output',
            'log',
        ]]

    def _patch(self, method):
        _m = patch.object(ceph_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    @patch('os.path.exists')
    def test_create_keyring(self, _exists):
        '''It creates a new ceph keyring'''
        _exists.return_value = False
        ceph_utils.create_keyring('cinder', 'cephkey')
        _cmd = ['ceph-authtool', '/etc/ceph/ceph.client.cinder.keyring',
                '--create-keyring', '--name=client.cinder',
                '--add-key=cephkey']
        self.check_call.assert_called_with(_cmd)

    @patch('os.path.exists')
    def test_create_keyring_already_exists(self, _exists):
        '''It creates a new ceph keyring'''
        _exists.return_value = True
        ceph_utils.create_keyring('cinder', 'cephkey')
        self.log.assert_called()
        self.check_call.assert_not_called()

    @patch('os.path.exists')
    def test_create_keyfile(self, _exists):
        '''It creates a new ceph keyfile'''
        _exists.return_value = False
        with patch_open() as (_open, _file):
            ceph_utils.create_key_file('cinder', 'cephkey')
            _file.write.assert_called_with('cephkey')
        self.log.assert_called()

    @patch('os.path.exists')
    def test_create_key_file_already_exists(self, _exists):
        '''It creates a new ceph keyring'''
        _exists.return_value = True
        ceph_utils.create_key_file('cinder', 'cephkey')
        self.log.assert_called()

    @patch('os.mkdir')
    @patch.object(ceph_utils, 'apt_install')
    @patch('os.path.exists')
    def test_install(self, _exists, _install, _mkdir):
        _exists.return_value = False
        ceph_utils.install()
        _mkdir.assert_called_with('/etc/ceph')
        _install.assert_called_with('ceph-common', fatal=True)

    def test_get_osds(self):
        self.check_output.return_value = json.dumps([1, 2, 3])
        self.assertEquals(ceph_utils.get_osds(), [1, 2, 3])

    def test_get_osds_none(self):
        self.check_output.return_value = json.dumps(None)
        self.assertEquals(ceph_utils.get_osds(), None)

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool(self, _exists, _get_osds):
        '''It creates rados pool correctly with default replicas '''
        _exists.return_value = False
        _get_osds.return_value = [1, 2, 3]
        ceph_utils.create_pool(service='cinder', name='foo')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', 150]),
            call(['ceph', '--id', 'cinder', 'osd', 'set',
                  'foo', 'size', 2])
        ])

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool_3_replicas(self, _exists, _get_osds):
        '''It creates rados pool correctly with 3 replicas'''
        _exists.return_value = False
        _get_osds.return_value = [1, 2, 3]
        ceph_utils.create_pool(service='cinder', name='foo', replicas=3)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', 100]),
            call(['ceph', '--id', 'cinder', 'osd', 'set',
                  'foo', 'size', 3])
        ])

    def test_create_pool_already_exists(self):
        self._patch('pool_exists')
        self.pool_exists.return_value = True
        ceph_utils.create_pool(service='cinder', name='foo')
        self.log.assert_called()
        self.check_call.assert_not_called()

    def test_keyring_path(self):
        '''It correctly dervies keyring path from service name'''
        result = ceph_utils._keyring_path('cinder')
        self.assertEquals('/etc/ceph/ceph.client.cinder.keyring', result)

    def test_keyfile_path(self):
        '''It correctly dervies keyring path from service name'''
        result = ceph_utils._keyfile_path('cinder')
        self.assertEquals('/etc/ceph/ceph.client.cinder.key', result)

    def test_pool_exists(self):
        '''It detects an rbd pool exists'''
        self.check_output.return_value = LS_POOLS
        self.assertTrue(ceph_utils.pool_exists('cinder', 'volumes'))

    def test_pool_does_not_exist(self):
        '''It detects an rbd pool exists'''
        self.check_output.return_value = LS_POOLS
        self.assertFalse(ceph_utils.pool_exists('cinder', 'foo'))

    def test_pool_exists_error(self):
        ''' Ensure subprocess errors and sandboxed with False '''
        self.check_output.side_effect = CalledProcessError(1, 'rados')
        self.assertFalse(ceph_utils.pool_exists('cinder', 'foo'))

    def test_rbd_exists(self):
        self.check_output.return_value = LS_RBDS
        self.assertTrue(ceph_utils.rbd_exists('service', 'pool', 'rbd1'))
        self.check_output.assert_call_with(
            ['rbd', 'list', '--id', 'service', '--pool', 'pool']
        )

    def test_rbd_does_not_exist(self):
        self.check_output.return_value = LS_RBDS
        self.assertFalse(ceph_utils.rbd_exists('service', 'pool', 'rbd4'))
        self.check_output.assert_call_with(
            ['rbd', 'list', '--id', 'service', '--pool', 'pool']
        )

    def test_rbd_exists_error(self):
        ''' Ensure subprocess errors and sandboxed with False '''
        self.check_output.side_effect = CalledProcessError(1, 'rbd')
        self.assertFalse(ceph_utils.rbd_exists('cinder', 'foo', 'rbd'))

    def test_create_rbd_image(self):
        ceph_utils.create_rbd_image('service', 'pool', 'image', 128)
        _cmd = ['rbd', 'create', 'image',
                '--size', '128',
                '--id', 'service',
                '--pool', 'pool']
        self.check_call.assert_called_with(_cmd)

    def test_delete_pool(self):
        ceph_utils.delete_pool('cinder', 'pool')
        _cmd = [
            'ceph', '--id', 'cinder',
            'osd', 'pool', 'delete',
            'pool', '--yes-i-really-really-mean-it'
        ]
        self.check_call.assert_called_with(_cmd)

    def test_get_ceph_nodes(self):
        self._patch('relation_ids')
        self._patch('related_units')
        self._patch('relation_get')
        units = ['ceph/1', 'ceph2', 'ceph/3']
        self.relation_ids.return_value = ['ceph:0']
        self.related_units.return_value = units
        self.relation_get.return_value = '192.168.1.1'
        self.assertEquals(len(ceph_utils.get_ceph_nodes()), 3)

    def test_get_ceph_nodes_not_related(self):
        self._patch('relation_ids')
        self.relation_ids.return_value = []
        self.assertEquals(ceph_utils.get_ceph_nodes(), [])

    def test_configure(self):
        self._patch('create_keyring')
        self._patch('create_key_file')
        self._patch('get_ceph_nodes')
        self._patch('modprobe')
        _hosts = ['192.168.1.1', '192.168.1.2']
        self.get_ceph_nodes.return_value = _hosts
        _conf = ceph_utils.CEPH_CONF.format(
            auth='cephx',
            keyring=ceph_utils._keyring_path('cinder'),
            mon_hosts=",".join(map(str, _hosts))
        )
        with patch_open() as (_open, _file):
            ceph_utils.configure('cinder', 'key', 'cephx')
            _file.write.assert_called_with(_conf)
            _open.assert_called_with('/etc/ceph/ceph.conf', 'w')
        self.modprobe.assert_called_with('rbd')
        self.create_keyring.assert_called_with('cinder', 'key')
        self.create_key_file.assert_called_with('cinder', 'key')

    def test_image_mapped(self):
        self.check_output.return_value = IMG_MAP
        self.assertTrue(ceph_utils.image_mapped('bar'))

    def test_image_not_mapped(self):
        self.check_output.return_value = IMG_MAP
        self.assertFalse(ceph_utils.image_mapped('foo'))

    def test_image_not_mapped_error(self):
        self.check_output.side_effect = CalledProcessError(1, 'rbd')
        self.assertFalse(ceph_utils.image_mapped('bar'))

    def test_map_block_storage(self):
        _service = 'cinder'
        _pool = 'bar'
        _img = 'foo'
        _cmd = [
            'rbd',
            'map',
            '{}/{}'.format(_pool, _img),
            '--user',
            _service,
            '--secret',
            ceph_utils._keyfile_path(_service),
        ]
        ceph_utils.map_block_storage(_service, _pool, _img)
        self.check_call.assert_called_with(_cmd)

    def test_modprobe(self):
        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            ceph_utils.modprobe('mymod')
            _open.assert_called_with('/etc/modules', 'r+')
            _file.read.assert_called()
            _file.write.assert_called_with('mymod')
        self.check_call.assert_called_with(['modprobe', 'mymod'])

    def test_filesystem_mounted(self):
        self._patch('mounts')
        self.mounts.return_value = [['/afs', '/dev/sdb'], ['/bfs', '/dev/sdd']]
        self.assertTrue(ceph_utils.filesystem_mounted('/afs'))
        self.assertFalse(ceph_utils.filesystem_mounted('/zfs'))

    def test_make_filesystem(self):
        ceph_utils.make_filesystem('/dev/sdd')
        self.log.assert_called()
        self.check_call.assert_called_with(['mkfs', '-t', 'ext4', '/dev/sdd'])

    def test_make_filesystem_xfs(self):
        ceph_utils.make_filesystem('/dev/sdd', 'xfs')
        self.log.assert_called()
        self.check_call.assert_called_with(['mkfs', '-t', 'xfs', '/dev/sdd'])

    @patch('os.chown')
    @patch('os.stat')
    def test_place_data_on_block_device(self, _stat, _chown):
        self._patch('mount')
        self._patch('copy_files')
        self._patch('umount')
        _stat.return_value.st_uid = 100
        _stat.return_value.st_gid = 100
        ceph_utils.place_data_on_block_device('/dev/sdd', '/var/lib/mysql')
        self.mount.assert_has_calls([
            call('/dev/sdd', '/mnt'),
            call('/dev/sdd', '/var/lib/mysql', persist=True)
        ])
        self.copy_files.assert_called_with('/var/lib/mysql', '/mnt')
        self.umount.assert_called_with('/mnt')
        _chown.assert_called_with('/var/lib/mysql', 100, 100)

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_is_dir(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest')
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     False, None)
            ])

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_include_symlinks(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest', True)
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     True, None)
            ])

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_ignore(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest', True, False)
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     True, False)
            ])

    @patch('shutil.copy2')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_files(self, _isdir, _listdir, _copy2):
        _isdir.return_value = False
        files = ['a', 'b', 'c']
        _listdir.return_value = files
        ceph_utils.copy_files('/source', '/dest')
        for f in files:
            _copy2.assert_has_calls([
                call('/source/{}'.format(f), '/dest/{}'.format(f))
            ])

    def test_ensure_ceph_storage(self):
        self._patch('pool_exists')
        self.pool_exists.return_value = False
        self._patch('create_pool')
        self._patch('rbd_exists')
        self.rbd_exists.return_value = False
        self._patch('create_rbd_image')
        self._patch('image_mapped')
        self.image_mapped.return_value = False
        self._patch('map_block_storage')
        self._patch('filesystem_mounted')
        self.filesystem_mounted.return_value = False
        self._patch('make_filesystem')
        self._patch('service_stop')
        self._patch('service_start')
        self._patch('service_running')
        self.service_running.return_value = True
        self._patch('place_data_on_block_device')
        _service = 'mysql'
        _pool = 'bar'
        _rbd_img = 'foo'
        _mount = '/var/lib/mysql'
        _services = ['mysql']
        _blk_dev = '/dev/rbd1'
        ceph_utils.ensure_ceph_storage(_service, _pool,
                                       _rbd_img, 1024, _mount,
                                       _blk_dev, 'ext4', _services)
        self.create_pool.assert_called_with(_service, _pool)
        self.create_rbd_image.assert_called_with(_service, _pool,
                                                 _rbd_img, 1024)
        self.map_block_storage.assert_called_with(_service, _pool, _rbd_img)
        self.make_filesystem.assert_called_with(_blk_dev, 'ext4')
        self.service_stop.assert_called_with(_services[0])
        self.place_data_on_block_device.assert_called_with(_blk_dev, _mount)
        self.service_start.assert_called_with(_services[0])
