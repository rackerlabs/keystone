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
from keystone import exception
from keystone import identity
from keystone import policy
from keystone import token
from keystone.common import wsgi


class InfoExtension(wsgi.ExtensionRouter):
    """Previously known as the OS-KSADM extension.

    Provides a bunch of CRUD operations for internal data types.

    """

    def add_routes(self, mapper):
        info_controller = InfoController()

        # User operations
        mapper.connect('/users/by_name/{user_name}',
                controller=info_controller,
                action='get_user_by_name',
                conditions=dict(method=['GET']))

        # Tenant operations
        mapper.connect('/tenants/by_name/{tenant_name}',
                controller=info_controller,
                action='get_tenant_by_name',
                conditions=dict(method=['GET']))


class InfoController(wsgi.Application):
    def __init__(self):
        self.identity_api = identity.Manager()
        self.token_api = token.Manager()
        self.policy_api = policy.Manager()
        super(InfoController, self).__init__()

    def get_user_by_name(self, context, user_name):
        self.assert_admin(context)
        user_ref = self.identity_api.get_user_by_name(context, user_name)
        if not user_ref:
            raise UserNotFound(user_name=user_name)
        return {'user': user_ref}

    def get_tenant_by_name(self, context, tenant_name):
        self.assert_admin(context)
        tenant_ref = self.identity_api.get_tenant_by_name(context, tenant_name)
        if not tenant_ref:
            raise TenantNotFound(tenant_name=tenant_name)
        return {'tenant': tenant_ref}


class UserNotFound(exception.NotFound):
    """Could not find user with name: %(user_name)s"""


class TenantNotFound(exception.NotFound):
    """Could not find a tenant with name: %(tenant_name)s"""
