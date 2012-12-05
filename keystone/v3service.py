# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

import uuid
import routes
import json

from keystone import config
from keystone import catalog
from keystone.common import cms
from keystone.common import logging
from keystone.common import wsgi
from keystone import exception
from keystone import identity
from keystone.openstack.common import timeutils
from keystone import policy
from keystone import token

LOG = logging.getLogger(__name__)


class V3Router(wsgi.ComposingRouter):
    def crud_routes(self, mapper, controller, collection_key, key):
        collection_path = '/%(collection_key)s' % {
            'collection_key': collection_key}
        entity_path = '/%(collection_key)s/{%(key)s_id}' % {
            'collection_key': collection_key,
            'key': key}

        mapper.connect(
            collection_path,
            controller=controller,
            action='create_%s' % key,
            conditions=dict(method=['POST']))
        mapper.connect(
            collection_path,
            controller=controller,
            action='list_%s' % collection_key,
            conditions=dict(method=['GET']))
        mapper.connect(
            entity_path,
            controller=controller,
            action='get_%s' % key,
            conditions=dict(method=['GET']))
        mapper.connect(
            entity_path,
            controller=controller,
            action='update_%s' % key,
            conditions=dict(method=['PATCH']))
        mapper.connect(
            entity_path,
            controller=controller,
            action='delete_%s' % key,
            conditions=dict(method=['DELETE']))

    def __init__(self):
        mapper = routes.Mapper()

        apis = dict(
            catalog_api=catalog.Manager(),
            identity_api=identity.Manager(),
            policy_api=policy.Manager(),
            token_api=token.Manager())

        # Catalog

        self.crud_routes(
            mapper,
            catalog.controllers.ServiceV3(**apis),
            'services',
            'service')

        self.crud_routes(
            mapper,
            catalog.controllers.EndpointV3(**apis),
            'endpoints',
            'endpoint')

        # Identity

        self.crud_routes(
            mapper,
            identity.controllers.DomainV3(**apis),
            'domains',
            'domain')

        project_controller = identity.controllers.ProjectV3(**apis)
        self.crud_routes(
            mapper,
            project_controller,
            'projects',
            'project')
        mapper.connect(
            '/users/{user_id}/projects',
            controller=project_controller,
            action='list_user_projects',
            conditions=dict(method=['GET']))

        self.crud_routes(
            mapper,
            identity.controllers.UserV3(**apis),
            'users',
            'user')

        self.crud_routes(
            mapper,
            identity.controllers.CredentialV3(**apis),
            'credentials',
            'credential')

        role_controller = identity.controllers.RoleV3(**apis)
        self.crud_routes(
            mapper,
            role_controller,
            'roles',
            'role')
        mapper.connect(
            '/projects/{project_id}/users/{user_id}/roles/{role_id}',
            controller=role_controller,
            action='create_grant',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/projects/{project_id}/users/{user_id}/roles/{role_id}',
            controller=role_controller,
            action='check_grant',
            conditions=dict(method=['HEAD']))
        mapper.connect(
            '/projects/{project_id}/users/{user_id}/roles',
            controller=role_controller,
            action='list_grants',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/projects/{project_id}/users/{user_id}/roles/{role_id}',
            controller=role_controller,
            action='revoke_grant',
            conditions=dict(method=['DELETE']))
        mapper.connect(
            '/domains/{domain_id}/users/{user_id}/roles/{role_id}',
            controller=role_controller,
            action='create_grant',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/domains/{domain_id}/users/{user_id}/roles/{role_id}',
            controller=role_controller,
            action='check_grant',
            conditions=dict(method=['HEAD']))
        mapper.connect(
            '/domains/{domain_id}/users/{user_id}/roles',
            controller=role_controller,
            action='list_grants',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/domains/{domain_id}/users/{user_id}/roles/{role_id}',
            controller=role_controller,
            action='revoke_grant',
            conditions=dict(method=['DELETE']))

        # Policy

        policy_controller = policy.controllers.PolicyV3(**apis)
        self.crud_routes(
            mapper,
            policy_controller,
            'policies',
            'policy')

        # Token

        """
        # v2.0 LEGACY
        mapper.connect('/tokens/{token_id}',
                       controller=auth_controller,
                       action='validate_token',
                       conditions=dict(method=['GET']))
        mapper.connect('/tokens/{token_id}',
                       controller=auth_controller,
                       action='validate_token_head',
                       conditions=dict(method=['HEAD']))
        mapper.connect('/tokens/{token_id}',
                       controller=auth_controller,
                       action='delete_token',
                       conditions=dict(method=['DELETE']))
        mapper.connect('/tokens/{token_id}/endpoints',
                       controller=auth_controller,
                       action='endpoints',
                       conditions=dict(method=['GET']))
        """

        super(V3Router, self).__init__(mapper, [])
