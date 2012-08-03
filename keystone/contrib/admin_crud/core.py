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

from keystone import catalog
from keystone.common import wsgi
from keystone import identity
from keystone import policy
from keystone import token


class CrudExtension(wsgi.ExtensionRouter):
    """Previously known as the OS-KSADM extension.

    Provides a bunch of CRUD operations for internal data types.

    """

    def add_routes(self, mapper):
        tenant_controller = identity.TenantController()
        user_controller = identity.UserController()
        role_controller = identity.RoleController()
        service_controller = catalog.ServiceController()
        endpoint_controller = catalog.EndpointController()

        # Tenant Operations
        mapper.connect(
            '/tenants',
            controller=tenant_controller,
            action='create_tenant',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/tenants/{tenant_id}',
            controller=tenant_controller,
            action='update_tenant',
            conditions=dict(method=['PUT', 'POST']))
        mapper.connect(
            '/tenants/{tenant_id}',
            controller=tenant_controller,
            action='delete_tenant',
            conditions=dict(method=['DELETE']))
        mapper.connect(
            '/tenants/{tenant_id}/users',
            controller=tenant_controller,
            action='get_tenant_users',
            conditions=dict(method=['GET']))

        # User Operations
        mapper.connect(
            '/users',
            controller=user_controller,
            action='get_users',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users',
            controller=user_controller,
            action='create_user',
            conditions=dict(method=['POST']))
        # NOTE(termie): not in diablo
        mapper.connect(
            '/users/{user_id}',
            controller=user_controller,
            action='update_user',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/users/{user_id}',
            controller=user_controller,
            action='delete_user',
            conditions=dict(method=['DELETE']))

        # COMPAT(diablo): the copy with no OS-KSADM is from diablo
        mapper.connect(
            '/users/{user_id}/password',
            controller=user_controller,
            action='set_user_password',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/users/{user_id}/OS-KSADM/password',
            controller=user_controller,
            action='set_user_password',
            conditions=dict(method=['PUT']))

        # COMPAT(diablo): the copy with no OS-KSADM is from diablo
        mapper.connect(
            '/users/{user_id}/tenant',
            controller=user_controller,
            action='update_user_tenant',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/users/{user_id}/OS-KSADM/tenant',
            controller=user_controller,
            action='update_user_tenant',
            conditions=dict(method=['PUT']))

        # COMPAT(diablo): the copy with no OS-KSADM is from diablo
        mapper.connect(
            '/users/{user_id}/enabled',
            controller=user_controller,
            action='set_user_enabled',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/users/{user_id}/OS-KSADM/enabled',
            controller=user_controller,
            action='set_user_enabled',
            conditions=dict(method=['PUT']))

        # User Roles
        mapper.connect(
            '/users/{user_id}/roles/OS-KSADM/{role_id}',
            controller=role_controller,
            action='add_role_to_user',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/users/{user_id}/roles/OS-KSADM/{role_id}',
            controller=role_controller,
            action='remove_role_from_user',
            conditions=dict(method=['DELETE']))

        # COMPAT(diablo): User Roles
        mapper.connect(
            '/users/{user_id}/roleRefs',
            controller=role_controller,
            action='get_role_refs',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/roleRefs',
            controller=role_controller,
            action='create_role_ref',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/users/{user_id}/roleRefs/{role_ref_id}',
            controller=role_controller,
            action='delete_role_ref',
            conditions=dict(method=['DELETE']))

        # User-Tenant Roles
        mapper.connect(
            '/tenants/{tenant_id}/users/{user_id}/roles/OS-KSADM/{role_id}',
            controller=role_controller,
            action='add_role_to_user',
            conditions=dict(method=['PUT']))
        mapper.connect(
            '/tenants/{tenant_id}/users/{user_id}/roles/OS-KSADM/{role_id}',
            controller=role_controller,
            action='remove_role_from_user',
            conditions=dict(method=['DELETE']))

        # Service Operations
        mapper.connect(
            '/OS-KSADM/services',
            controller=service_controller,
            action='get_services',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-KSADM/services',
            controller=service_controller,
            action='create_service',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/OS-KSADM/services/{service_id}',
            controller=service_controller,
            action='delete_service',
            conditions=dict(method=['DELETE']))
        mapper.connect(
            '/OS-KSADM/services/{service_id}',
            controller=service_controller,
            action='get_service',
            conditions=dict(method=['GET']))

        # Endpoint Templates
        mapper.connect(
            '/endpoints',
            controller=endpoint_controller,
            action='get_endpoints',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/endpoints',
            controller=endpoint_controller,
            action='create_endpoint',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/endpoints/{endpoint_id}',
            controller=endpoint_controller,
            action='delete_endpoint',
            conditions=dict(method=['DELETE']))

        # Role Operations
        mapper.connect(
            '/OS-KSADM/roles',
            controller=role_controller,
            action='create_role',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/OS-KSADM/roles',
            controller=role_controller,
            action='get_roles',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-KSADM/roles/{role_id}',
            controller=role_controller,
            action='get_role',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-KSADM/roles/{role_id}',
            controller=role_controller,
            action='delete_role',
            conditions=dict(method=['DELETE']))


class CrudExtensionV3(CrudExtension):
    def add_routes(self, mapper):
        super(CrudExtensionV3, self).add_routes(mapper)

        catalog_api = catalog.Manager()
        identity_api = identity.Manager()
        policy_api = policy.Manager()
        token_api = token.Manager()

        # Policy Operations

        policy_controller = policy.PolicyControllerV3(
            catalog_api=catalog_api,
            identity_api=identity_api,
            policy_api=policy_api,
            token_api=token_api)

        mapper.connect(
            '/policies',
            controller=policy_controller,
            action='create_policy',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/policies',
            controller=policy_controller,
            action='list_policies',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/policies/{policy_id}',
            controller=policy_controller,
            action='get_policy',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/policies/{policy_id}',
            controller=policy_controller,
            action='update_policy',
            conditions=dict(method=['PATCH']))
        mapper.connect(
            '/policies/{policy_id}',
            controller=policy_controller,
            action='delete_policy',
            conditions=dict(method=['DELETE']))

        # Catalog

        service_controller = catalog.ServiceControllerV3(
            catalog_api=catalog_api,
            identity_api=identity_api,
            policy_api=policy_api,
            token_api=token_api)
        endpoint_controller = catalog.EndpointControllerV3(
            catalog_api=catalog_api,
            identity_api=identity_api,
            policy_api=policy_api,
            token_api=token_api)

        mapper.connect(
            '/services',
            controller=service_controller,
            action='create_service',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/services',
            controller=service_controller,
            action='list_services',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/services/{service_id}',
            controller=service_controller,
            action='get_service',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/services/{service_id}',
            controller=service_controller,
            action='update_service',
            conditions=dict(method=['PATCH']))
        mapper.connect(
            '/services/{service_id}',
            controller=service_controller,
            action='delete_service',
            conditions=dict(method=['DELETE']))
        mapper.connect(
            '/services/{service_id}/endpoints',
            controller=endpoint_controller,
            action='create_endpoint',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/services/{service_id}/endpoints',
            controller=endpoint_controller,
            action='list_endpoints',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/services/{service_id}/endpoints/{endpoint_id}',
            controller=endpoint_controller,
            action='get_endpoint',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/services/{service_id}/endpoints/{endpoint_id}',
            controller=endpoint_controller,
            action='update_endpoint',
            conditions=dict(method=['PATCH']))
        mapper.connect(
            '/services/{service_id}/endpoints/{endpoint_id}',
            controller=endpoint_controller,
            action='delete_endpoint',
            conditions=dict(method=['DELETE']))
