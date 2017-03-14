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

"""Main entry point into the Federation service."""

import uuid

from keystone.common import cache
from keystone.common import dependency
from keystone.common import driver_hints
from keystone.common import extension
from keystone.common import manager
import keystone.conf
from keystone import exception
from keystone.federation import utils
from keystone.i18n import _


# This is a general cache region for service providers.
MEMOIZE = cache.get_memoization_decorator(group='federation')

CONF = keystone.conf.CONF
EXTENSION_DATA = {
    'name': 'OpenStack Federation APIs',
    'namespace': 'https://docs.openstack.org/identity/api/ext/'
                 'OS-FEDERATION/v1.0',
    'alias': 'OS-FEDERATION',
    'updated': '2013-12-17T12:00:0-00:00',
    'description': 'OpenStack Identity Providers Mechanism.',
    'links': [{
        'rel': 'describedby',
        'type': 'text/html',
        'href': 'https://developer.openstack.org/api-ref-identity-v3-ext.html',
    }]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)
extension.register_public_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


@dependency.provider('federation_api')
@dependency.requires('identity_api', 'resource_api')
class Manager(manager.Manager):
    """Default pivot point for the Federation backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.federation'

    def __init__(self):
        super(Manager, self).__init__(CONF.federation.driver)

    def create_idp(self, idp_id, idp):
        if not idp.get('domain_id'):
            idp['domain_id'] = self._create_idp_domain(idp_id)
        else:
            self._assert_valid_domain_id(idp['domain_id'])
        return self.driver.create_idp(idp_id, idp)

    def _create_idp_domain(self, idp_id):
        domain_id = uuid.uuid4().hex
        desc = 'Auto generated federated domain for Identity Provider: '
        desc += idp_id
        domain = {
            'id': domain_id,
            'name': domain_id,
            'description': desc,
            'enabled': True
        }
        self.resource_api.create_domain(domain['id'], domain)
        return domain_id

    def _assert_valid_domain_id(self, domain_id):
        self.resource_api.get_domain(domain_id)

    def delete_idp(self, idp_id):
        """Delete an identity provider.

        Before we delete the identity provider, we need to remove all
        the federated_users that reference it. To do this we
        call the delete function for these entities, which are
        themselves responsible for deleting any additional data
        associated with them.

        :param idp_id: identity provider ID
        """
        fed_users_list = self._list_federated_users(idp_id=idp_id)
        self._delete_federated_users(fed_users_list)
        self.driver.delete_idp(idp_id)

    def _list_federated_users(self, idp_id=None, protocol_id=None):
        hints = driver_hints.Hints()
        if idp_id:
            hints.add_filter('idp_id', idp_id)
        if protocol_id:
            hints.add_filter('protocol_id', protocol_id)
        return self.identity_api.list_users(hints=hints)

    def _delete_federated_users(self, fed_users_list):
        for fed_users in fed_users_list:
            self.identity_api.delete_user(fed_users['id'])

    @MEMOIZE
    def get_enabled_service_providers(self):
        """List enabled service providers for Service Catalog.

        Service Provider in a catalog contains three attributes: ``id``,
        ``auth_url``, ``sp_url``, where:

        - id is a unique, user defined identifier for service provider object
        - auth_url is an authentication URL of remote Keystone
        - sp_url a URL accessible at the remote service provider where SAML
          assertion is transmitted.

        :returns: list of dictionaries with enabled service providers
        :rtype: list of dicts

        """
        def normalize(sp):
            ref = {
                'auth_url': sp.auth_url,
                'id': sp.id,
                'sp_url': sp.sp_url
            }
            return ref

        service_providers = self.driver.get_enabled_service_providers()
        return [normalize(sp) for sp in service_providers]

    def create_sp(self, sp_id, service_provider):
        sp_ref = self.driver.create_sp(sp_id, service_provider)
        self.get_enabled_service_providers.invalidate(self)
        return sp_ref

    def delete_sp(self, sp_id):
        self.driver.delete_sp(sp_id)
        self.get_enabled_service_providers.invalidate(self)

    def update_sp(self, sp_id, service_provider):
        sp_ref = self.driver.update_sp(sp_id, service_provider)
        self.get_enabled_service_providers.invalidate(self)
        return sp_ref

    def evaluate(self, idp_id, protocol_id, assertion_data):
        mapping = self.get_mapping_from_idp_and_protocol(idp_id, protocol_id)
        rules = mapping['rules']
        rule_processor = utils.RuleProcessor(mapping['id'], rules)
        mapped_properties = rule_processor.process(assertion_data)
        return mapped_properties, mapping['id']

    def create_protocol(self, idp_id, protocol_id, protocol):
        self._validate_mapping_exists(protocol['mapping_id'])
        return self.driver.create_protocol(idp_id, protocol_id, protocol)

    def update_protocol(self, idp_id, protocol_id, protocol):
        self._validate_mapping_exists(protocol['mapping_id'])
        return self.driver.update_protocol(idp_id, protocol_id, protocol)

    def _validate_mapping_exists(self, mapping_id):
        try:
            self.driver.get_mapping(mapping_id)
        except exception.MappingNotFound:
            msg = _('Invalid mapping id: %s')
            raise exception.ValidationError(message=(msg % mapping_id))

    def delete_protocol(self, idp_id, protocol_id):
        """Delete a protocol.

        Before we delete the protocol, we need to remove all
        the federated_users that reference it. To do this we
        call the delete function for these entities, which are
        themselves responsible for deleting any additional data
        associated with them.

        :param idp_id: the ID of the identity provider associated to
                       the protocol
        :param protocol_id: protocol ID
        """
        fed_users_list = self._list_federated_users(
            idp_id=idp_id, protocol_id=protocol_id)
        self._delete_federated_users(fed_users_list)
        self.driver.delete_protocol(idp_id, protocol_id)
