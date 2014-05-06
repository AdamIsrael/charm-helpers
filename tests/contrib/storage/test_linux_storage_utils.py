from mock import patch
import unittest

import charmhelpers.contrib.storage.linux.utils as storage_utils

# It's a mouthful.
STORAGE_LINUX_UTILS = 'charmhelpers.contrib.storage.linux.utils'


class MiscStorageUtilsTests(unittest.TestCase):

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    @patch(STORAGE_LINUX_UTILS + '.call')
    @patch(STORAGE_LINUX_UTILS + '.check_call')
    def test_zap_disk(self, check_call, call, check_output):
        '''It calls sgdisk correctly to zap disk'''
        check_output.return_value = '200\n'
        storage_utils.zap_disk('/dev/foo')
        call.assert_any_call(['sgdisk', '--zap-all', '--mbrtogpt',
                              '--clear', '/dev/foo'])
        check_output.assert_any_call(['blockdev', '--getsz', '/dev/foo'])
        check_call.assert_any_call(['dd', 'if=/dev/zero', 'of=/dev/foo',
                                    'bs=1M', 'count=1'])
        check_call.assert_any_call(['dd', 'if=/dev/zero', 'of=/dev/foo',
                                    'bs=512', 'count=100', 'seek=100'])

    @patch(STORAGE_LINUX_UTILS + '.stat')
    @patch(STORAGE_LINUX_UTILS + '.S_ISBLK')
    def test_is_block_device(self, s_isblk, stat):
        '''It detects device node is block device'''
        with patch(STORAGE_LINUX_UTILS + '.S_ISBLK') as isblk:
            isblk.return_value = True
            self.assertTrue(storage_utils.is_block_device('/dev/foo'))

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted(self, check_output):
        '''It detects mounted devices as mounted.'''
        check_output.return_value = (
            "/dev/sda1 on / type ext4 (rw,errors=remount-ro)\n")
        result = storage_utils.is_device_mounted('/dev/sda')
        self.assertTrue(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_not_mounted(self, check_output):
        '''It detects unmounted devices as mounted.'''
        check_output.return_value = (
            "/dev/foo on / type ext4 (rw,errors=remount-ro)\n")
        result = storage_utils.is_device_mounted('/dev/sda')
        self.assertFalse(result)
