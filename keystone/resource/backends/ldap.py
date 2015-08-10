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

from __future__ import absolute_import

import uuid

from oslo_config import cfg
from oslo_log import log
from oslo_log import versionutils

from keystone.common import clean
from keystone.common import driver_hints
from keystone.common import ldap as common_ldap
from keystone.common import models
from keystone import exception
from keystone.i18n import _
from keystone.identity.backends import ldap as ldap_identity
from keystone import resource


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Resource(resource.ResourceDriverV8):
    @versionutils.deprecated(
        versionutils.deprecated.LIBERTY,
        remove_in=+1,
        what='ldap resource')
    def __init__(self):
        super(Resource, self).__init__()
        self.LDAP_URL = CONF.ldap.url
        self.LDAP_USER = CONF.ldap.user
        self.LDAP_PASSWORD = CONF.ldap.password
        self.suffix = CONF.ldap.suffix

        # This is the only deep dependency from resource back to identity.
        # This is safe to do since if you are using LDAP for resource, it is
        # required that you are using it for identity as well.
        self.user = ldap_identity.UserApi(CONF)

        self.project = ProjectApi(CONF)

    def default_assignment_driver(self):
        return 'ldap'

    def _set_default_parent_project(self, ref):
        # If the parent project ID has not been set, set it to domain
        # default.
        default_domain = resource.calc_default_domain_project()

        if isinstance(ref, dict):
            if 'parent_id' not in ref:
                if ref['id'] == CONF.identity.default_domain_id:
                    ref = dict(ref, parent_id=None)
                else:
                    ref = dict(ref, parent_id=default_domain.get('id'))
            return ref
        elif isinstance(ref, list):
            return [self._set_default_parent_project(x) for x in ref]
        else:
            raise ValueError(_('Expected dict or list: %s') % type(ref))

    def _set_default_is_domain_project(self, ref):
        if isinstance(ref, dict):
            if ref['id'] == CONF.identity.default_domain_id:
                return dict(ref, is_domain=True)
            else:
                return dict(ref, is_domain=False)
        elif isinstance(ref, list):
            return [self._set_default_is_domain_project(x) for x in ref]
        else:
            raise ValueError(_('Expected dict or list: %s') % type(ref))

    def _validate_parent_project(self, ref):
        # If a parent_id different from Domain Default or None was given,
        # raise InvalidProjectException.
        parent_id = ref.get('parent_id')
        domain_default = resource.calc_default_domain()
        if parent_id and parent_id != domain_default['id']:
            raise exception.InvalidParentProject(parent_id)

    def _validate_is_domain_field_is_false(self, ref):
        is_domain = ref.pop('is_domain', None)
        if is_domain:
            raise exception.ValidationError(_('LDAP does not support projects '
                                              'with is_domain flag enabled'))

    def _set_default_attributes(self, project_ref):
        project_ref = self._set_default_domain(project_ref)
        project_ref = self._set_default_is_domain_project(project_ref)
        return self._set_default_parent_project(project_ref)

    def get_project(self, tenant_id):
        if tenant_id == CONF.identity.default_domain_id:
            return resource.calc_default_domain_project()

        return self._set_default_attributes(self.project.get(tenant_id))

    def _filter_project(self, project_ref, filters):
        for f in filters:
            if project_ref.get(f['name']) != f['value']:
                return False
        return True

    def list_projects(self, hints):
        filters = hints.filters[:]
        projects = self._set_default_attributes(
            self.project.get_all_filtered(hints))
        projects.append(resource.calc_default_domain_project())
        return [p for p in projects if self._filter_project(p, filters)]

    def list_projects_in_domain(self, domain_id):
        hints = driver_hints.Hints()
        hints.add_filter('domain_id', domain_id)
        return self._set_default_attributes(self.list_projects(hints))

    def list_projects_acting_as_domain(self, hints):
        return [resource.calc_default_domain_project()]

    def list_projects_in_subtree(self, project_id):
        return self.list_projects_in_domain(project_id)

    def list_project_parents(self, project_id):
        if project_id != CONF.identity.default_domain_id:
            return [resource.calc_default_domain_project()]
        return []

    def is_leaf_project(self, project_id):
        return project_id != CONF.identity.default_domain_id

    def list_projects_from_ids(self, ids, is_domain=False):
        if not is_domain:
            return [self.get_project(id) for id in ids]

        if CONF.identity.default_domain_id in ids:
            return [resource.calc_default_domain_project()]
        return []

    def list_project_ids_from_domain_ids(self, domain_ids):
        if CONF.identity.default_domain_id in domain_ids:
            return [x.id for x in self.list_projects_in_domain(
                CONF.identity.default_domain_id)]
        return []

    def get_project_by_name(self, tenant_name, domain_id, is_domain):
        if is_domain:
            # Check if the provided name matches the default domain project one
            domain_project = resource.calc_default_domain_project()
            if tenant_name != domain_project['name']:
                raise exception.ProjectNotFound(project_id=tenant_name)
            return domain_project

        self._validate_default_domain_id(domain_id)
        return self._set_default_attributes(
            self.project.get_by_name(tenant_name))

    def create_project(self, tenant_id, tenant):
        if tenant.get('is_domain'):
            self.create_domain(tenant_id, tenant)

        self.project.check_allow_create()
        self._validate_parent_project(tenant)
        self._validate_is_domain_field_is_false(tenant)
        tenant['name'] = clean.project_name(tenant['name'])
        data = tenant.copy()
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4().hex)
        if 'description' in data and data['description'] in ['', None]:
            data.pop('description')
        return self._set_default_attributes(
            self.project.create(data))

    def update_project(self, tenant_id, tenant):
        self.project.check_allow_update()
        if tenant_id == CONF.identity.default_domain_id:
            self.update_domain(tenant_id, tenant)
        tenant = self._validate_default_domain(tenant)
        self._validate_is_domain_field_is_false(tenant)
        if 'name' in tenant:
            tenant['name'] = clean.project_name(tenant['name'])
        if 'is_domain' in tenant:
            tenant.pop('is_domain')
        if 'parent_id' in tenant:
            tenant.pop('parent_id')
        return self._set_default_attributes(
            self.project.update(tenant_id, tenant))

    def delete_project(self, tenant_id):
        if tenant_id == CONF.identity.default_domain_id:
            self.delete_domain(tenant_id)

        self.project.check_allow_delete()
        if self.project.subtree_delete_enabled:
            self.project.deleteTree(tenant_id)
        else:
            # The manager layer will call assignments to delete the
            # role assignments, so we just have to delete the project itself.
            self.project.delete(tenant_id)

    def create_domain(self, domain_id, domain):
        if domain_id == CONF.identity.default_domain_id:
            msg = _('Duplicate ID, %s.') % domain_id
            raise exception.Conflict(type='domain', details=msg)
        raise exception.Forbidden(_('Domains are read-only against LDAP'))

    def get_domain(self, domain_id):
        self._validate_default_domain_id(domain_id)
        return resource.calc_default_domain()

    def update_domain(self, domain_id, domain):
        self._validate_default_domain_id(domain_id)
        raise exception.Forbidden(_('Domains are read-only against LDAP'))

    def delete_domain(self, domain_id):
        self._validate_default_domain_id(domain_id)
        raise exception.Forbidden(_('Domains are read-only against LDAP'))

    def list_domains(self, hints):
        return [resource.calc_default_domain()]

    def list_domains_from_ids(self, ids):
        return [resource.calc_default_domain()]

    def get_domain_by_name(self, domain_name):
        default_domain = resource.calc_default_domain()
        if domain_name != default_domain['name']:
            raise exception.DomainNotFound(domain_id=domain_name)
        return default_domain


# TODO(termie): turn this into a data object and move logic to driver
class ProjectApi(common_ldap.ProjectLdapStructureMixin,
                 common_ldap.EnabledEmuMixIn, common_ldap.BaseLdap):

    model = models.Project

    def create(self, values):
        data = values.copy()
        if data.get('id') is None:
            data['id'] = uuid.uuid4().hex
        return super(ProjectApi, self).create(data)

    def update(self, project_id, values):
        old_obj = self.get(project_id)
        return super(ProjectApi, self).update(project_id, values, old_obj)

    def get_all_filtered(self, hints):
        query = self.filter_query(hints)
        return super(ProjectApi, self).get_all(query)
