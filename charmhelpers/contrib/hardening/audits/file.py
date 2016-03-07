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
import grp
import os
import pwd
import re

from subprocess import (
    CalledProcessError,
    check_output,
    check_call,
)
from traceback import format_exc
from six import string_types
from stat import (
    S_ISGID,
    S_ISUID
)

from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
)

from charmhelpers.core import unitdata
from charmhelpers.core.host import file_hash

from charmhelpers.contrib.hardening.audits import BaseAudit
from charmhelpers.contrib.hardening.templating import render_and_write
from charmhelpers.contrib.hardening import utils


class BaseFileAudit(BaseAudit):
    """Implements base file audits."""

    def __init__(self, paths, force_compliance=False, *args, **kwargs):
        super(BaseFileAudit, self).__init__(*args, **kwargs)
        self.force_compliance = force_compliance
        if isinstance(paths, string_types) or not hasattr(paths, '__iter__'):
            self.paths = [paths]
        else:
            self.paths = paths

    def ensure_compliance(self):
        for p in self.paths:
            if os.path.exists(p):
                if self.is_compliant(p):
                    continue

                log('File %s is not in compliance.' % p, level=INFO)
            else:
                if not self.force_compliance:
                    log("Skipping compliance check for non-existent path '%s'"
                        % (p), level=INFO)
                    continue

            if self._take_action():
                log("Applying compliance criteria to '%s'" % (p), level=INFO)
                self.comply(p)

    def is_compliant(self, path):
        """Audits the path to see if it is compliance.

        :param path: the path to the file that should be checked.
        """
        raise NotImplementedError

    def comply(self, path):
        """Enforces the compliance of a path.

        :param path: the path to the file that should be enforced.
        """
        raise NotImplementedError

    @classmethod
    def _get_stat(cls, path):
        """Returns the Posix st_stat information for the specified file path.

        :param path: the path to get the st_stat information for.
        :returns: an st_stat object for the path or None if the path doesn't
                  exist.
        """
        return os.stat(path)


class FilePermissionAudit(BaseFileAudit):
    """Implements an audit for file permissions and ownership for a user.

    This class implements functionality that ensures that a specific user/group
    will own the file(s) specified and that the permissions specified are
    applied properly to the file.
    """
    def __init__(self, paths, user, group=None, mode=0o600, **kwargs):
        self.user = user
        self.group = group
        self.mode = mode
        super(FilePermissionAudit, self).__init__(paths, user, group, mode,
                                                  **kwargs)

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, name):
        try:
            user = pwd.getpwnam(name)
        except KeyError:
            log('Unknown user %s' % name, level=ERROR)
            user = None
        self._user = user

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, name):
        try:
            group = None
            if name:
                group = grp.getgrnam(name)
            else:
                group = grp.getgrgid(self.user.pw_gid)
        except KeyError:
            log('Unknown group %s' % name, level=ERROR)
        self._group = group

    def is_compliant(self, path):
        """Checks if the path is in compliance.

        Used to determine if the path specified meets the necessary
        requirements to be in compliance with the check itself.

        :param path: the file path to check
        :returns: True if the path is compliant, False otherwise.
        """
        stat = self._get_stat(path)
        user = self.user
        group = self.group

        compliant = True
        if stat.st_uid != user.pw_uid or stat.st_gid != group.gr_gid:
            log('File %s is not owned by %s:%s.' % (path, user.pw_name,
                                                    group.gr_name),
                level=INFO)
            compliant = False

        # POSIX refers to the st_mode bits as corresponding to both the
        # file type and file permission bits, where the least significant 12
        # bits (o7777) are the suid (11), guid (10), sticky bits (9), and the
        # file permission bits (8-0)
        perms = stat.st_mode & 0o7777
        if perms != self.mode:
            log('File %s has incorrect permissions, currently set to %s' %
                (path, oct(stat.st_mode & 0o7777)), level=INFO)
            compliant = False

        return compliant

    def comply(self, path):
        """Issues a chown and chmod to the file paths specified."""
        utils.ensure_permissions(path, self.user.pw_name, self.group.gr_name,
                                 self.mode)


class DirectoryPermissionAudit(FilePermissionAudit):
    """Performs a permission check for the  specified directory path."""

    def __init__(self, paths, user, group=None, mode=0o600,
                 recursive=True, **kwargs):
        super(DirectoryPermissionAudit, self).__init__(paths, user, group,
                                                       mode, **kwargs)
        self.recursive = recursive

    def is_compliant(self, path):
        """Checks if the directory is compliant.

        Used to determine if the path specified and all of its children
        directories are in compliance with the check itself.

        :param path: the directory path to check
        :returns: True if the directory tree is compliant, False otherewise.
        """
        if not os.path.isdir(path):
            log('Path specified %s is not a directory.' % path, level=ERROR)
            raise ValueError("%s is not a directory." % path)

        if not self.recursive:
            return super(DirectoryPermissionAudit, self).is_compliant(path)

        compliant = True
        for root, dirs, _ in os.walk(path):
            if len(dirs) > 0:
                continue

            if not super(DirectoryPermissionAudit, self).is_compliant(root):
                compliant = False
                continue

        return compliant

    def comply(self, path):
        for root, dirs, _ in os.walk(path):
            if len(dirs) > 0:
                super(DirectoryPermissionAudit, self).comply(root)


class ReadOnly(BaseFileAudit):
    """Audits that files and folders are read only."""
    def __init__(self, paths, *args, **kwargs):
        super(ReadOnly, self).__init__(paths=paths, *args, **kwargs)

    def is_compliant(self, path):
        try:
            output = check_output(['find', path, '-perm', '-go+w',
                                   '-type', 'f']).strip()

            # The find above will find any files which have permission sets
            # which allow too broad of write access. As such, the path is
            # compliant if there is no output.
            if output:
                return False
            else:
                return True
        except CalledProcessError as e:
            log('Error occurred checking finding writable files for %s. '
                'Error information is: command %s failed with returncode '
                '%d and output %s.\n%s' % (path, e.cmd, e.returncode, e.output,
                                           format_exc(e)), level=ERROR)
            return False

    def comply(self, path):
        try:
            check_output(['chmod', 'go-w', '-R', path])
        except CalledProcessError as e:
            log('Error occurred removing writeable permissions for %s. '
                'Error information is: command %s failed with returncode '
                '%d and output %s.\n%s' % (path, e.cmd, e.returncode, e.output,
                                           format_exc(e)), level=ERROR)


class NoSUIDSGIDAudit(BaseFileAudit):
    """Audits that specified files do not have SUID/GUID bits set."""
    def __init__(self, paths, *args, **kwargs):
        super(NoSUIDSGIDAudit, self).__init__(paths=paths, *args, **kwargs)

    def is_compliant(self, path):
        stat = self._get_stat(path)
        if (stat.st_mode & (S_ISGID | S_ISUID)) != 0:
            return False
        else:
            return True

    def comply(self, path):
        try:
            log('Removing suid/guid from %s.' % path)
            check_output(['chmod', '-s', path])
        except CalledProcessError as e:
            log('Error occurred removing suid/sgid from %s.'
                'Error information is: command %s failed with returncode '
                '%d and output %s.\n%s' % (path, e.cmd, e.returncode, e.output,
                                           format_exc(e)), level=ERROR)


class TemplatedFile(BaseFileAudit):
    """The TemplatedFileAudit audits the contents of a templated file.

    This audit renders a file from a template, sets the appropriate file
    permissions, then generates a hashsum with which to check the content
    changed.
    """
    def __init__(self, path, context, template_dir, mode, user='root',
                 group='root', service_actions=None, **kwargs):
        self.context = context
        self.user = user
        self.group = group
        self.mode = mode
        self.template_dir = template_dir
        self.service_actions = service_actions
        super(TemplatedFile, self).__init__(paths=path, force_compliance=True,
                                            **kwargs)

    def is_compliant(self, path):
        """Determines if the templated file is compliant.

        A templated file is only compliant if it has not changed (as
        determined by its sha256 hashsum) AND its file permissions are set
        appropriately.

        :param path: the path to check compliance.
        """
        same_content = self.contents_match(path)
        same_permissions = self.permissions_match(path)

        if same_content and same_permissions:
            return True
        else:
            return False

    def run_service_actions(self):
        """Run any actions on services requested."""
        if not self.service_actions:
            return

        for svc_action in self.service_actions:
            name = svc_action['service']
            actions = svc_action['actions']
            log("Running service '%s' actions '%s'" % (name, actions),
                level=DEBUG)
            for action in actions:
                cmd = ['sudo', 'service', name, action]
                try:
                    check_call(cmd)
                except CalledProcessError as exc:
                    log("Service name='%s' action='%s' failed - %s" %
                        (name, action, exc), level=WARNING)

    def comply(self, path):
        """Ensures the contents and the permissions of the file.

        :param path: the path to correct
        """
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        self.pre_write()
        render_and_write(self.template_dir, path, self.context())
        utils.ensure_permissions(path, self.user, self.group, self.mode)
        self.run_service_actions()
        self.save_checksum(path)
        self.post_write()

    def pre_write(self):
        """Invoked prior to writing the template."""
        pass

    def post_write(self):
        """Invoked after writing the template."""
        pass

    def contents_match(self, path):
        """Determines if the file content is the same.

        This is determined by comparing hashsum of the file contents and
        the saved hashsum. If there is no hashsum, then the content cannot
        be sure to be the same so treat them as if they are not the same.
        Otherwise, return True if the hashsums are the same, False if they
        are not the same.

        :param path: the file to check.
        """
        checksum = file_hash(path)

        kv = unitdata.kv()
        stored_checksum = kv.get('hardening:%s' % path)
        if not stored_checksum:
            # If the checksum hasn't been generated, return False to ensure
            # the file is written and the checksum stored.
            log('Checksum for %s has not been calculated.' % path, level=DEBUG)
            return False
        elif stored_checksum != checksum:
            log('Checksum mismatch for %s.' % path, level=DEBUG)
            return False
        else:
            return True

    def permissions_match(self, path):
        """Determines if the file owner and permissions match.

        :param path: the path to check.
        """
        audit = FilePermissionAudit(path, self.user, self.group, self.mode)
        return audit.is_compliant(path)

    def save_checksum(self, path):
        """Calculates and saves the checksum for the path specified.

        :param path: the path of the file to save the checksum.
        """
        checksum = file_hash(path)
        kv = unitdata.kv()
        kv.set('hardening:%s' % path, checksum)
        kv.flush()


class DeletedFile(BaseFileAudit):
    """Audit to ensure that a file is deleted."""
    def __init__(self, paths):
        super(DeletedFile, self).__init__(paths)

    def is_compliant(self, path):
        return not os.path.exists(path)

    def comply(self, path):
        os.remove(path)


class FileContentAudit(BaseFileAudit):
    """Audit the contents of a file."""
    def __init__(self, paths, patterns, **kwargs):
        self.patterns = patterns
        super(FileContentAudit, self).__init__(paths, **kwargs)

    def is_compliant(self, path):
        log("Auditing contents of file '%s'" % (path), level=DEBUG)
        compliant = True
        with open(path, 'r') as fd:
            contents = fd.read()

        for pattern in self.patterns:
            key = re.compile(pattern)
            results = re.search(key, contents, flags=re.MULTILINE)
            if not results:
                compliant = False

        return compliant
