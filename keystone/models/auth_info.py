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

import sys

from oslo_config import cfg
from oslo_log import log
import six

from keystone.common import dependency
from keystone.common import utils
from keystone import exception
from keystone.i18n import _


CONF = cfg.CONF
LOG = log.getLogger(__name__)

# registry of authentication methods
AUTH_METHODS = {}
AUTH_PLUGINS_LOADED = False


@dependency.requires('resource_api', 'trust_api')
class AuthInfo(object):
    """Encapsulation of "auth" request."""

    @staticmethod
    def create(context, auth=None, scope_only=False):
        auth_info = AuthInfo(context, auth=auth)
        auth_info._validate_and_normalize_auth_data(scope_only)
        return auth_info

    def __init__(self, context, auth=None):
        self.context = context
        self.auth = auth
        self._scope_data = (None, None, None, None)
        # self._scope_data is (domain_id, project_id, trust_ref, unscoped)
        # project scope: (None, project_id, None, None)
        # domain scope: (domain_id, None, None, None)
        # trust scope: (None, None, trust_ref, None)
        # unscoped: (None, None, None, 'unscoped')

    def _assert_project_is_enabled(self, project_ref):
        # ensure the project is enabled
        try:
            self.resource_api.assert_project_enabled(
                project_id=project_ref['id'],
                project=project_ref)
        except AssertionError as e:
            LOG.warning(six.text_type(e))
            six.reraise(exception.Unauthorized, exception.Unauthorized(e),
                        sys.exc_info()[2])

    def _assert_domain_is_enabled(self, domain_ref):
        try:
            self.resource_api.assert_domain_enabled(
                domain_id=domain_ref['id'],
                domain=domain_ref)
        except AssertionError as e:
            LOG.warning(six.text_type(e))
            six.reraise(exception.Unauthorized, exception.Unauthorized(e),
                        sys.exc_info()[2])

    def _lookup_domain(self, domain_info):
        domain_id = domain_info.get('id')
        domain_name = domain_info.get('name')
        domain_ref = None
        if not domain_id and not domain_name:
            raise exception.ValidationError(attribute='id or name',
                                            target='domain')
        try:
            if domain_name:
                if (CONF.resource.domain_name_url_safe == 'strict' and
                        utils.is_not_url_safe(domain_name)):
                    msg = _('Domain name cannot contain reserved characters.')
                    raise exception.Unauthorized(message=msg)
                domain_ref = self.resource_api.get_domain_by_name(
                    domain_name)
            else:
                domain_ref = self.resource_api.get_domain(domain_id)
        except exception.DomainNotFound as e:
            LOG.exception(six.text_type(e))
            raise exception.Unauthorized(e)
        self._assert_domain_is_enabled(domain_ref)
        return domain_ref

    def _lookup_project(self, project_info):
        project_id = project_info.get('id')
        project_name = project_info.get('name')
        project_ref = None
        if not project_id and not project_name:
            raise exception.ValidationError(attribute='id or name',
                                            target='project')
        try:
            if project_name:
                if (CONF.resource.project_name_url_safe == 'strict' and
                        utils.is_not_url_safe(project_name)):
                    msg = _('Project name cannot contain reserved characters.')
                    raise exception.Unauthorized(message=msg)
                if 'domain' not in project_info:
                    raise exception.ValidationError(attribute='domain',
                                                    target='project')
                domain_ref = self._lookup_domain(project_info['domain'])
                project_ref = self.resource_api.get_project_by_name(
                    project_name, domain_ref['id'])
            else:
                project_ref = self.resource_api.get_project(project_id)
                # NOTE(morganfainberg): The _lookup_domain method will raise
                # exception.Unauthorized if the domain isn't found or is
                # disabled.
                self._lookup_domain({'id': project_ref['domain_id']})
        except exception.ProjectNotFound as e:
            raise exception.Unauthorized(e)
        self._assert_project_is_enabled(project_ref)
        return project_ref

    def _lookup_trust(self, trust_info):
        trust_id = trust_info.get('id')
        if not trust_id:
            raise exception.ValidationError(attribute='trust_id',
                                            target='trust')
        trust = self.trust_api.get_trust(trust_id)
        return trust

    def _validate_and_normalize_scope_data(self):
        """Validate and normalize scope data."""
        if 'scope' not in self.auth:
            return
        if sum(['project' in self.auth['scope'],
                'domain' in self.auth['scope'],
                'unscoped' in self.auth['scope'],
                'OS-TRUST:trust' in self.auth['scope']]) != 1:
            raise exception.ValidationError(
                attribute='project, domain, OS-TRUST:trust or unscoped',
                target='scope')
        if 'unscoped' in self.auth['scope']:
            self._scope_data = (None, None, None, 'unscoped')
            return
        if 'project' in self.auth['scope']:
            project_ref = self._lookup_project(self.auth['scope']['project'])
            self._scope_data = (None, project_ref['id'], None, None)
        elif 'domain' in self.auth['scope']:
            domain_ref = self._lookup_domain(self.auth['scope']['domain'])
            self._scope_data = (domain_ref['id'], None, None, None)
        elif 'OS-TRUST:trust' in self.auth['scope']:
            if not CONF.trust.enabled:
                raise exception.Forbidden('Trusts are disabled.')
            trust_ref = self._lookup_trust(
                self.auth['scope']['OS-TRUST:trust'])
            # TODO(ayoung): when trusts support domains, fill in domain data
            if trust_ref.get('project_id') is not None:
                project_ref = self._lookup_project(
                    {'id': trust_ref['project_id']})
                self._scope_data = (None, project_ref['id'], trust_ref, None)
            else:
                self._scope_data = (None, None, trust_ref, None)

    def _validate_auth_methods(self):
        if 'identity' not in self.auth:
            raise exception.ValidationError(attribute='identity',
                                            target='auth')

        # make sure auth methods are provided
        if 'methods' not in self.auth['identity']:
            raise exception.ValidationError(attribute='methods',
                                            target='identity')

        # make sure all the method data/payload are provided
        for method_name in self.get_method_names():
            if method_name not in self.auth['identity']:
                raise exception.ValidationError(attribute=method_name,
                                                target='identity')

        # make sure auth method is supported
        for method_name in self.get_method_names():
            if method_name not in AUTH_METHODS:
                raise exception.AuthMethodNotSupported()

    def _validate_and_normalize_auth_data(self, scope_only=False):
        """Make sure "auth" is valid.

        :param scope_only: If it is True, auth methods will not be
                           validated but only the scope data.
        :type scope_only: boolean
        """
        # make sure "auth" exist
        if not self.auth:
            raise exception.ValidationError(attribute='auth',
                                            target='request body')

        # NOTE(chioleong): Tokenless auth does not provide auth methods,
        # we only care about using this method to validate the scope
        # information. Therefore, validating the auth methods here is
        # insignificant and we can skip it when scope_only is set to
        # true.
        if scope_only is False:
            self._validate_auth_methods()
        self._validate_and_normalize_scope_data()

    def get_method_names(self):
        """Returns the identity method names.

        :returns: list of auth method names

        """
        # Sanitizes methods received in request's body
        # Filters out duplicates, while keeping elements' order.
        method_names = []
        for method in self.auth['identity']['methods']:
            if method not in method_names:
                method_names.append(method)
        return method_names

    def get_method_data(self, method):
        """Get the auth method payload.

        :returns: auth method payload

        """
        if method not in self.auth['identity']['methods']:
            raise exception.ValidationError(attribute=method,
                                            target='identity')
        return self.auth['identity'][method]

    def get_scope(self):
        """Get scope information.

        Verify and return the scoping information.

        :returns: (domain_id, project_id, trust_ref, unscoped).
                   If scope to a project, (None, project_id, None, None)
                   will be returned.
                   If scoped to a domain, (domain_id, None, None, None)
                   will be returned.
                   If scoped to a trust, (None, project_id, trust_ref, None),
                   Will be returned, where the project_id comes from the
                   trust definition.
                   If unscoped, (None, None, None, 'unscoped') will be
                   returned.

        """
        return self._scope_data

    def set_scope(self, domain_id=None, project_id=None, trust=None,
                  unscoped=None):
        """Set scope information."""
        if domain_id and project_id:
            msg = _('Scoping to both domain and project is not allowed')
            raise ValueError(msg)
        if domain_id and trust:
            msg = _('Scoping to both domain and trust is not allowed')
            raise ValueError(msg)
        if project_id and trust:
            msg = _('Scoping to both project and trust is not allowed')
            raise ValueError(msg)
        self._scope_data = (domain_id, project_id, trust, unscoped)
