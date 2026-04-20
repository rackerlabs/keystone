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
from keystone.common import provider_api
import keystone.conf
from keystone import exception
from keystone.i18n import _

CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)
PROVIDERS = provider_api.ProviderAPIs

VALID_TARGET_TYPES = ('user', 'domain', 'project')


class Manager(manager.Manager):
    """Manager for IP CIDR allowlists per user, domain, or project.

    Provides business logic on top of the pluggable backend driver.
    """

    driver_namespace = 'keystone.ip_allowlist'
    _provides_api = 'ip_allowlist_api'

    def __init__(self):
        super().__init__(CONF.ip_allowlist.driver)

    @staticmethod
    def _resolve_ip(ip_address):
        try:
            return ipaddress.ip_address(ip_address)
        except (TypeError, ValueError):
            LOG.warning('Invalid source IP address %s', ip_address)
            return None

    def _ip_matches_entries(
        self, addr, entries, target_type, target_id
    ):
        for entry in entries:
            try:
                network = ipaddress.ip_network(entry['cidr'], strict=False)
            except ValueError:
                LOG.warning(
                    'Invalid CIDR %(cidr)s in allowlist for '
                    '%(type)s %(id)s',
                    {
                        'cidr': entry['cidr'],
                        'type': target_type,
                        'id': target_id,
                    },
                )
                continue
            if addr in network:
                return True
        return False

    def _check_target(self, ip_address, target_type, target_id):
        """Return True if the target allows the IP, False otherwise.

        A target with no entries is open (returns True).
        """
        entries = self.driver.list_allowed_cidrs(target_type, target_id)
        if not entries:
            return True
        addr = self._resolve_ip(ip_address)
        if addr is None:
            return False
        return self._ip_matches_entries(
            addr, entries, target_type, target_id
        )

    def enforce_authentication(self, user_id, user_domain_id, ip_address):
        """Check authentication-level allowlists (user, user's home domain).

        :raises keystone.exception.IPAddressNotAllowed: If denied (401).
        """
        if not self._check_target(ip_address, 'user', user_id):
            LOG.warning(
                'IP %(ip)s denied for user %(user)s; not in user allowlist',
                {'ip': ip_address, 'user': user_id},
            )
            raise exception.IPAddressNotAllowed()
        if user_domain_id and not self._check_target(
            ip_address, 'domain', user_domain_id
        ):
            LOG.warning(
                'IP %(ip)s denied for user %(user)s home domain %(dom)s',
                {
                    'ip': ip_address,
                    'user': user_id,
                    'dom': user_domain_id,
                },
            )
            raise exception.IPAddressNotAllowed()

    def enforce_authorization(
        self, ip_address, project_id=None, domain_id=None
    ):
        """Check scope-level allowlists (scoped domain/project).

        For a project-scoped request, ``project_id`` is checked along with
        the project's parent domain. For a domain-scoped request, the
        given ``domain_id`` is checked. Unscoped requests are a no-op.

        :raises keystone.exception.IPAddressNotAllowedForScope: If denied
            (403).
        """
        if project_id:
            project = PROVIDERS.resource_api.get_project(project_id)
            project_domain_id = project.get('domain_id')
            if project_domain_id and not self._check_target(
                ip_address, 'domain', project_domain_id
            ):
                LOG.warning(
                    'IP %(ip)s denied for scope: domain %(dom)s of '
                    'project %(proj)s',
                    {
                        'ip': ip_address,
                        'dom': project_domain_id,
                        'proj': project_id,
                    },
                )
                raise exception.IPAddressNotAllowedForScope()
            if not self._check_target(ip_address, 'project', project_id):
                LOG.warning(
                    'IP %(ip)s denied for scope: project %(proj)s',
                    {'ip': ip_address, 'proj': project_id},
                )
                raise exception.IPAddressNotAllowedForScope()
        elif domain_id:
            if not self._check_target(ip_address, 'domain', domain_id):
                LOG.warning(
                    'IP %(ip)s denied for scope: domain %(dom)s',
                    {'ip': ip_address, 'dom': domain_id},
                )
                raise exception.IPAddressNotAllowedForScope()

    def list_allowed_cidrs(self, target_type, target_id):
        self._validate_target_type(target_type)
        return self.driver.list_allowed_cidrs(target_type, target_id)

    def get_allowed_cidr(self, target_type, target_id, entry_id):
        self._validate_target_type(target_type)
        return self.driver.get_allowed_cidr(
            target_type, target_id, entry_id
        )

    def create_allowed_cidr(self, target_type, target_id, entry):
        self._validate_target_type(target_type)
        cidr = entry.get('cidr')
        if cidr is None:
            raise exception.ValidationError(attribute='cidr', target='cidr')
        try:
            ipaddress.ip_network(cidr, strict=False)
        except (TypeError, ValueError):
            raise exception.ValidationError(
                attribute=_('a valid CIDR for cidr'), target='cidr'
            )
        entry_id = uuid.uuid4().hex
        entry.setdefault('created_at', timeutils.utcnow())
        return self.driver.create_allowed_cidr(
            target_type, target_id, entry_id, entry
        )

    def delete_allowed_cidr(self, target_type, target_id, entry_id):
        self._validate_target_type(target_type)
        self.driver.delete_allowed_cidr(target_type, target_id, entry_id)

    @staticmethod
    def _validate_target_type(target_type):
        if target_type not in VALID_TARGET_TYPES:
            raise exception.ValidationError(
                attribute=_('one of %s') % (VALID_TARGET_TYPES,),
                target='target_type',
            )
