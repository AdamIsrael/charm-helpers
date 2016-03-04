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
from charmhelpers.contrib.hardening.audits.file import TemplatedFile
from charmhelpers.contrib.hardening.host import TEMPLATES_DIR
from charmhelpers.contrib.hardening import utils


def get_audits():
    """Returns the audits and checks necessary to secure the TTY."""
    audits = []

    defaults = utils.get_defaults('os')

    # If core dumps are not enabled, then don't allow core dumps to be
    # created as they may contain sensitive information.
    if not defaults.get('enable_core_dump', False):
        audits.append(TemplatedFile('/etc/profile.d/pinerolo_profile.sh',
                                    ProfileContext(),
                                    template_dir=TEMPLATES_DIR,
                                    mode=0o0755, user='root', group='root'))
    return audits


class ProfileContext(object):

    def __call__(self):
        ctxt = {}
        return ctxt
