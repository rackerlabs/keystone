# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Main entry point into the IP Allowlist service."""

import ipaddress
import uuid

from oslo_log import log
from oslo_utils import timeutils

from keystone.common import manager
import keystone.conf
from keystone import exception
from keystone.i18n import _

CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


class Manager(manager.Manager):
    """Manager for per-user IP CIDR allowlists.

    Provides business logic on top of the pluggable backend driver.
    """

    driver_namespace = 'keystone.ip_allowlist'
    _provides_api = 'ip_allowlist_api'

    def __init__(self):
        super().__init__(CONF.ip_allowlist.driver)

    def check_ip_allowed(self, user_id, ip_address):
        """Check whether *ip_address* is permitted for *user_id*.

        If the user has no CIDR entries the request is allowed (open access).
        Otherwise the IP must match at least one CIDR or an
        ``Unauthorized`` exception is raised.

        :param user_id: The user whose allowlist to check.
        :param ip_address: The source IP as a string (v4 or v6).
        :raises keystone.exception.Unauthorized: If the IP is not allowed.
        """
        entries = self.driver.list_allowed_cidrs(user_id)
        if not entries:
            return

        try:
            addr = ipaddress.ip_address(ip_address)
        except ValueError:
            LOG.warning(
                'Invalid source IP address %(ip)s for user %(user)s',
                {'ip': ip_address, 'user': user_id},
            )
            raise exception.Unauthorized(
                _('Unable to verify source IP address.')
            )

        for entry in entries:
            try:
                network = ipaddress.ip_network(entry['cidr'], strict=False)
            except ValueError:
                LOG.warning(
                    'Invalid CIDR %(cidr)s in allowlist for user %(user)s',
                    {'cidr': entry['cidr'], 'user': user_id},
                )
                continue
            if addr in network:
                return

        LOG.warning(
            'IP %(ip)s denied for user %(user)s; not in allowlist',
            {'ip': ip_address, 'user': user_id},
        )
        raise exception.Unauthorized(
            _('Source IP address is not in the allowlist.')
        )

    def list_allowed_cidrs(self, user_id):
        return self.driver.list_allowed_cidrs(user_id)

    def get_allowed_cidr(self, user_id, entry_id):
        return self.driver.get_allowed_cidr(user_id, entry_id)

    def create_allowed_cidr(self, user_id, entry):
        entry_id = uuid.uuid4().hex
        entry.setdefault('created_at', timeutils.utcnow())
        return self.driver.create_allowed_cidr(user_id, entry_id, entry)

    def delete_allowed_cidr(self, user_id, entry_id):
        self.driver.delete_allowed_cidr(user_id, entry_id)
