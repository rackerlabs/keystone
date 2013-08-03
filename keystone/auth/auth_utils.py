# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 OpenStack Foundation
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

from keystone import exception

from keystone.common import dependency
from keystone.openstack.common import log

LOG = log.getLogger(__name__)


@dependency.requires('assignment_api', 'identity_api',
                     'credential_api', 'trust_api')
class AuthUtils(object):
    def _assert_resource_is_enabled(self, resource_name, ref):
        if not ref.get('enabled', True):
            msg = _('%(resource_name)s is disabled: %(resource_id)s') % (
                {'resource_name': resource_name, 'resource_id': ref['id']})
            LOG.warning(msg)
            raise exception.Unauthorized(msg)

    def assert_project_is_enabled(self, project_ref):
        self._assert_resource_is_enabled('Project', project_ref)

    def assert_domain_is_enabled(self, domain_ref):
        self._assert_resource_is_enabled('Domain', domain_ref)

    def assert_user_is_enabled(self, user_ref):
        self._assert_resource_is_enabled('User', user_ref)

    # TODO(gyee): need to enhance backend to do filter by project_id for
    # list credentials instead of doing it here
    def lookup_credential(self, credential_id, project_id=None):
        creds = self.credential_api.get_credential(credential_id)
        if creds.get('project_id') and creds['project_id'] != project_id:
            msg = _('Credential %(credential_id)s is scoped to '
                    'project %(scoped_project_id)s. It is not permitted for '
                    'project %(request_project_id)s.') % (
                        {'credential_id': credential_id,
                         'scoped_project_id': creds['project_id'],
                         'request_project_id': project_id})
            raise exception.Unauthorized(message=msg)
        return creds

    def get_utf8_value(self, value):
        """Get the UTF8-encoded version of a value."""
        if not isinstance(value, str) and not isinstance(value, unicode):
            value = str(value)
        if isinstance(value, unicode):
            return value.encode('utf-8')
        else:
            return value

    def lookup_domain(self, domain_info):
        domain_id = domain_info.get('id')
        domain_name = domain_info.get('name')
        domain_ref = None
        if not domain_id and not domain_name:
            raise exception.ValidationError(attribute='id or name',
                                            target='domain')
        try:
            if domain_name:
                domain_ref = self.identity_api.get_domain_by_name(domain_name)
            else:
                domain_ref = self.identity_api.get_domain(domain_id)
        except exception.DomainNotFound as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)
        self.assert_domain_is_enabled(domain_ref)
        return domain_ref

    def lookup_project(self, project_info):
        project_id = project_info.get('id')
        project_name = project_info.get('name')
        project_ref = None
        if not project_id and not project_name:
            raise exception.ValidationError(attribute='id or name',
                                            target='project')
        try:
            if project_name:
                if 'domain' not in project_info:
                    raise exception.ValidationError(attribute='domain',
                                                    target='project')
                domain_ref = self.lookup_domain(project_info['domain'])
                project_ref = self.assignment_api.get_project_by_name(
                    project_name, domain_ref['id'])
            else:
                project_ref = self.identity_api.get_project(project_id)
        except exception.ProjectNotFound as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)
        self.assert_project_is_enabled(project_ref)
        return project_ref

    def lookup_trust(self, trust_info):
        trust_id = trust_info.get('id')
        if not trust_id:
            raise exception.ValidationError(attribute='trust_id',
                                            target='trust')
        trust = self.trust_api.get_trust(trust_id)
        if not trust:
            raise exception.TrustNotFound(trust_id=trust_id)
        return trust

    def lookup_user(self, user_info):
        user_id = user_info.get('id')
        user_name = user_info.get('name')
        user_ref = None
        if not user_id and not user_name:
            raise exception.ValidationError(attribute='id or name',
                                            target='user')
        try:
            if user_name:
                if 'domain' not in user_info:
                    raise exception.ValidationError(attribute='domain',
                                                    target='user')
                domain_ref = self.lookup_domain(user_info['domain'])
                user_ref = self.identity_api.get_user_by_name(
                    user_name, domain_ref['id'])
            else:
                user_ref = self.identity_api.get_user(user_id)
                domain_ref = self.identity_api.get_domain(
                    user_ref['domain_id'])
        except exception.UserNotFound as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)
        self.assert_domain_is_enabled(domain_ref)
        self.assert_user_is_enabled(user_ref)
        return user_ref, domain_ref
