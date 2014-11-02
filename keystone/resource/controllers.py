# Copyright 2013 Metacloud, Inc.
# Copyright 2012 OpenStack Foundation
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

"""Workflow Logic the Resource service."""

import uuid

from keystone.common import controller
from keystone.common import dependency
from keystone.common import validation
from keystone import config
from keystone import exception
from keystone.i18n import _
from keystone.openstack.common import log
from keystone.resource import schema


CONF = config.CONF
LOG = log.getLogger(__name__)


@dependency.requires('resource_api')
class Tenant(controller.V2Controller):

    @controller.v2_deprecated
    def get_all_projects(self, context, **kw):
        """Gets a list of all tenants for an admin user."""
        if 'name' in context['query_string']:
            return self.get_project_by_name(
                context, context['query_string'].get('name'))

        self.assert_admin(context)
        tenant_refs = self.resource_api.list_projects_in_domain(
            CONF.identity.default_domain_id)
        for tenant_ref in tenant_refs:
            tenant_ref = self.filter_domain_id(tenant_ref)
        params = {
            'limit': context['query_string'].get('limit'),
            'marker': context['query_string'].get('marker'),
        }
        return self.format_project_list(tenant_refs, **params)

    @controller.v2_deprecated
    def get_project(self, context, tenant_id):
        # TODO(termie): this stuff should probably be moved to middleware
        self.assert_admin(context)
        ref = self.resource_api.get_project(tenant_id)
        return {'tenant': self.filter_domain_id(ref)}

    @controller.v2_deprecated
    def get_project_by_name(self, context, tenant_name):
        self.assert_admin(context)
        ref = self.resource_api.get_project_by_name(
            tenant_name, CONF.identity.default_domain_id)
        return {'tenant': self.filter_domain_id(ref)}

    # CRUD Extension
    @controller.v2_deprecated
    def create_project(self, context, tenant):
        tenant_ref = self._normalize_dict(tenant)

        if 'name' not in tenant_ref or not tenant_ref['name']:
            msg = _('Name field is required and cannot be empty')
            raise exception.ValidationError(message=msg)

        self.assert_admin(context)
        tenant_ref['id'] = tenant_ref.get('id', uuid.uuid4().hex)
        tenant = self.resource_api.create_project(
            tenant_ref['id'],
            self._normalize_domain_id(context, tenant_ref))
        return {'tenant': self.filter_domain_id(tenant)}

    @controller.v2_deprecated
    def update_project(self, context, tenant_id, tenant):
        self.assert_admin(context)
        # Remove domain_id if specified - a v2 api caller should not
        # be specifying that
        clean_tenant = tenant.copy()
        clean_tenant.pop('domain_id', None)

        tenant_ref = self.resource_api.update_project(
            tenant_id, clean_tenant)
        return {'tenant': tenant_ref}

    @controller.v2_deprecated
    def delete_project(self, context, tenant_id):
        self.assert_admin(context)
        self.resource_api.delete_project(tenant_id)


@dependency.requires('resource_api')
class Role(controller.V2Controller):

    # CRUD extension
    @controller.v2_deprecated
    def get_role(self, context, role_id):
        self.assert_admin(context)
        return {'role': self.resource_api.get_role(role_id)}

    @controller.v2_deprecated
    def create_role(self, context, role):
        role = self._normalize_dict(role)
        self.assert_admin(context)

        if 'name' not in role or not role['name']:
            msg = _('Name field is required and cannot be empty')
            raise exception.ValidationError(message=msg)

        role_id = uuid.uuid4().hex
        role['id'] = role_id
        role_ref = self.resource_api.create_role(role_id, role)
        return {'role': role_ref}

    @controller.v2_deprecated
    def delete_role(self, context, role_id):
        self.assert_admin(context)
        self.resource_api.delete_role(role_id)

    @controller.v2_deprecated
    def get_roles(self, context):
        self.assert_admin(context)
        return {'roles': self.resource_api.list_roles()}


@dependency.requires('resource_api')
class DomainV3(controller.V3Controller):
    collection_name = 'domains'
    member_name = 'domain'

    def __init__(self):
        super(DomainV3, self).__init__()
        self.get_member_from_driver = self.resource_api.get_domain

    @controller.protected()
    @validation.validated(schema.domain_create, 'domain')
    def create_domain(self, context, domain):
        ref = self._assign_unique_id(self._normalize_dict(domain))
        ref = self.resource_api.create_domain(ref['id'], ref)
        return DomainV3.wrap_member(context, ref)

    @controller.filterprotected('enabled', 'name')
    def list_domains(self, context, filters):
        hints = DomainV3.build_driver_hints(context, filters)
        refs = self.resource_api.list_domains(hints=hints)
        return DomainV3.wrap_collection(context, refs, hints=hints)

    @controller.protected()
    def get_domain(self, context, domain_id):
        ref = self.resource_api.get_domain(domain_id)
        return DomainV3.wrap_member(context, ref)

    @controller.protected()
    @validation.validated(schema.domain_update, 'domain')
    def update_domain(self, context, domain_id, domain):
        self._require_matching_id(domain_id, domain)
        ref = self.resource_api.update_domain(domain_id, domain)
        return DomainV3.wrap_member(context, ref)

    @controller.protected()
    def delete_domain(self, context, domain_id):
        return self.resource_api.delete_domain(domain_id)


@dependency.requires('resource_api')
class ProjectV3(controller.V3Controller):
    collection_name = 'projects'
    member_name = 'project'

    def __init__(self):
        super(ProjectV3, self).__init__()
        self.get_member_from_driver = self.resource_api.get_project

    @controller.protected()
    @validation.validated(schema.project_create, 'project')
    def create_project(self, context, project):
        ref = self._assign_unique_id(self._normalize_dict(project))
        ref = self._normalize_domain_id(context, ref)
        ref = self.resource_api.create_project(ref['id'], ref)
        return ProjectV3.wrap_member(context, ref)

    @controller.filterprotected('domain_id', 'enabled', 'name')
    def list_projects(self, context, filters):
        hints = ProjectV3.build_driver_hints(context, filters)
        refs = self.resource_api.list_projects(hints=hints)
        return ProjectV3.wrap_collection(context, refs, hints=hints)

    @controller.protected()
    def get_project(self, context, project_id):
        ref = self.resource_api.get_project(project_id)
        return ProjectV3.wrap_member(context, ref)

    @controller.protected()
    @validation.validated(schema.project_update, 'project')
    def update_project(self, context, project_id, project):
        self._require_matching_id(project_id, project)
        self._require_matching_domain_id(
            project_id, project, self.resource_api.get_project)
        ref = self.resource_api.update_project(project_id, project)
        return ProjectV3.wrap_member(context, ref)

    @controller.protected()
    def delete_project(self, context, project_id):
        return self.resource_api.delete_project(project_id)


@dependency.requires('resource_api')
class RoleV3(controller.V3Controller):
    collection_name = 'roles'
    member_name = 'role'

    def __init__(self):
        super(RoleV3, self).__init__()
        self.get_member_from_driver = self.resource_api.get_role

    @controller.protected()
    @validation.validated(schema.role_create, 'role')
    def create_role(self, context, role):
        ref = self._assign_unique_id(self._normalize_dict(role))
        ref = self.resource_api.create_role(ref['id'], ref)
        return RoleV3.wrap_member(context, ref)

    @controller.filterprotected('name')
    def list_roles(self, context, filters):
        hints = RoleV3.build_driver_hints(context, filters)
        refs = self.resource_api.list_roles(
            hints=hints)
        return RoleV3.wrap_collection(context, refs, hints=hints)

    @controller.protected()
    def get_role(self, context, role_id):
        ref = self.resource_api.get_role(role_id)
        return RoleV3.wrap_member(context, ref)

    @controller.protected()
    @validation.validated(schema.role_update, 'role')
    def update_role(self, context, role_id, role):
        self._require_matching_id(role_id, role)

        ref = self.resource_api.update_role(role_id, role)
        return RoleV3.wrap_member(context, ref)

    @controller.protected()
    def delete_role(self, context, role_id):
        self.resource_api.delete_role(role_id)
