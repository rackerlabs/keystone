# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
#
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

from keystone.common import wsgi
from keystone.contrib.federation import controllers


class FederationExtension(wsgi.ExtensionRouter):
    """API Endpoints for the Federation extension.

    The API looks like:
    #TODO(marek-denis): Add API for Idp
    """

    def add_routes(self, mapper):
        federation_controller = controllers.IdentityProvider()
        publickey_controller = controllers.ProviderPublicKey()
        protocol_controller = controllers.FederationProtocol()

## Identity Providers CRUD operations
        mapper.connect(
            '/OS-IDP/identity_providers',
            controller=federation_controller,
            action='create_federated_provider',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/OS-IDP/identity_providers',
            controller=federation_controller,
            action='list_federated_providers',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}',
            controller=federation_controller,
            action='get_federated_provider',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}',
            controller=federation_controller,
            action='delete_federated_provider',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}',
            controller=federation_controller,
            action='update_federated_provider',
            conditions=dict(method=['PATCH']))

## Public keys CRUD operations
        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/public_keys',
            controller=publickey_controller,
            action='put_provider_key',
            conditions=dict(method=['PUT']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/public_keys/{key_id}',
            controller=publickey_controller,
            action='update_provider_key',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/public_keys',
            controller=publickey_controller,
            action='list_provider_keys',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/public_keys/{key_id}',
            controller=publickey_controller,
            action='get_provider_key',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/public_keys/{key_id}',
            controller=publickey_controller,
            action='delete_provider_key',
            conditions=dict(method=['DELETE']))

## Protocol CRUD operations
        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/protocols',
            controller=protocol_controller,
            action='put_protocol',
            conditions=dict(method=['PUT']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/protocols/{protocol_id}',
            controller=protocol_controller,
            action='update_protocol',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/protocols/{protocol_id}',
            controller=protocol_controller,
            action='get_protocol',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/protocols',
            controller=protocol_controller,
            action='list_protocols',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-IDP/identity_providers/{idp_id}/protocols/{protocol_id}',
            controller=protocol_controller,
            action='delete_protocol',
            conditions=dict(method=['DELETE']))
