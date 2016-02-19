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

import glob
import os
import pwd

from charmhelpers.core.hookenv import (
    log,
    WARNING,
)


def ensure_permissions(path, user, permissions, maxdepth=-1):
    """Ensure permissions for path.

    If path is a file, apply to file and return.

    If path is a directory, recursively apply to directory contents and return.

    NOTE: a negative maxdepth e.g. -1 gives infinite recursion.
    """
    if not os.path.exists(path):
        log("File '%s' does not exist - cannot set permissions" % (path),
            level=WARNING)
        return

    user = pwd.getpwnam(user)
    os.chown(path, user.pw_uid, user.pw_gid)
    os.chmod(path, permissions)

    if maxdepth == 0:
        log("Max recursion depth reached - skipping further recursion")
        return
    elif maxdepth > 0:
        maxdepth -= 1

    if os.path.isdir(path):
        contents = glob.glob("%s/*" % (path))
        for c in contents:
            ensure_permissions(c, user=user, permissions=permissions,
                               maxdepth=maxdepth)
