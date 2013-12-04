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
     POST /OS-FEDERATION/identity_providers
     GET /OS-FEDERATION/identity_providers
     GET /OS-FEDERATION/identity_providers/$identity_providers
     DELETE /OS-FEDERATION/identity_providers/$identity_provider
     PATCH /OS-FEDERATION/identity_providers/$identity_providers

     GET /OS-FEDERATION/identity_providers/
         $identity_providers/protocols
     GET /OS-FEDERATION/identity_providers/
         $identity_providers/protocols/$protocol
     PUT /OS-FEDERATION/identity_providers/
         $identity_providers/protocols/$protocol
     PATCH /OS-FEDERATION/identity_providers/
         $identity_providers/protocols/$protocol
     DELETE /OS-FEDERATION/identity_providers/
         $identity_providers/protocols/$protocol

     POST /OS-FEDERATION/mappings
     GET /OS-FEDERATION/mappings
     PATCH /OS-FEDERATION/mappings/$mapping_id
     GET /OS-FEDERATION/mappings/$mapping_id
     DELETE /OS-FEDERATION/mappings/$mapping_id

    """

    def add_routes(self, mapper):
        idp_controller = controllers.IdentityProvider()
        protocol_controller = controllers.FederationProtocol()
        mapping_controller = controllers.MappingController()

        ## Identity Providers CRUD operations
        mapper.connect(
            '/OS-FEDERATION/identity_providers',
            controller=idp_controller,
            action='create_federated_provider',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers',
            controller=idp_controller,
            action='list_federated_providers',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}',
            controller=idp_controller,
            action='get_federated_provider',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}',
            controller=idp_controller,
            action='delete_federated_provider',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}',
            controller=idp_controller,
            action='update_federated_provider',
            conditions=dict(method=['PATCH']))

        ## Protocol CRUD operations
        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}/'
            'protocols/{protocol_id}',
            controller=protocol_controller,
            action='put_protocol',
            conditions=dict(method=['PUT']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}/'
            'protocols/{protocol_id}',
            controller=protocol_controller,
            action='update_protocol',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}/'
            'protocols/{protocol_id}',
            controller=protocol_controller,
            action='get_protocol',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}/'
            'protocols',
            controller=protocol_controller,
            action='list_protocols',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-FEDERATION/identity_providers/{idp_id}/'
            'protocols/{protocol_id}',
            controller=protocol_controller,
            action='delete_protocol',
            conditions=dict(method=['DELETE']))

        # Mapping CRUD operations
        mapper.connect(
            '/OS-FEDERATION/mappings',
            controller=mapping_controller,
            action='create_mapping',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/OS-FEDERATION/mappings',
            controller=mapping_controller,
            action='list_mappings',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-FEDERATION/mappings/{mapping_id}',
            controller=mapping_controller,
            action='get_mapping',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-FEDERATION/mappings/{mapping_id}',
            controller=mapping_controller,
            action='delete_mapping',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/OS-FEDERATION/mappings/{mapping_id}',
            controller=mapping_controller,
            action='update_mapping',
            conditions=dict(method=['PATCH']))
