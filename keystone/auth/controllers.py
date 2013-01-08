# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

from keystone import config
from keystone import exception
from keystone import identity
from keystone.common import controller
from keystone.common import dependency
from keystone.common import logging
from keystone.openstack.common import importutils
from keystone.auth import token_factory
from keystone.token import controllers as token_controllers
from keystone.token import core


LOG = logging.getLogger(__name__)

CONF = config.CONF

# registry of authentication methods
AUTH_METHODS = {}


# register method drivers
for method_name in CONF.auth.methods:
    try:
        config.register_str(method_name, group='auth')
    except Exception as e:
        LOG.exception(e)


def load_auth_method(method_name):
    if method_name in CONF.auth.methods:
        driver = CONF.auth.get(method_name)
        return importutils.import_object(driver)
    else:
        raise exception.AuthMethodNotSupported()


def get_auth_method(method_name):
    global AUTH_METHODS
    if method_name not in AUTH_METHODS:
        AUTH_METHODS[method_name] = load_auth_method(method_name)
    return AUTH_METHODS[method_name]


class AuthInfo(object):
    """ Encapsulation of "auth" request. """

    def __init__(self, context, auth=None):
        self.identity_api = identity.Manager()
        self.context = context
        self.auth = auth
        # scope data is (domain_id, project_id)
        # project scope: (None, project_id)
        # domain scope: (domain_id, None)
        # unscoped: (None, None)
        self._scope_data = (None, None)
        self._validate_and_normalize_auth_data()

    def _assert_project_is_enabled(self, project_ref):
        # making sure the project is enabled
        if not project_ref.get('enabled', True):
            msg = _('Project is disabled: %s') % project_ref['id']
            LOG.warning(msg)
            raise exception.Unauthorized(msg)
        # TODO(gyee): making sure the project's domain is enabled
        #project_domain_ref = self.identity_api.get_domain(
        #    self.context, project_ref['domain_id'])
        #self._assert_domain_is_enabled(project_domain_ref)

    def _assert_domain_is_enabled(self, domain_ref):
        if not domain_ref.get('enabled', True):
            msg = _('Domain is disabled: %s') % (domain_ref['id'])
            LOG.warning(msg)
            raise exception.Unauthorized(msg)

    def _validate_and_normalize_scope_data(self):
        """ Validate and normalize scope data """
        if 'scope' not in self.auth:
            return                

        # if scoped, only to a project or domain, but not both
        if 'project' not in self.auth['scope'] and \
           'domain' not in self.auth['scope']:
            # neither domain or project provided
            raise exception.ValidationError(attribute='project or domain',
                                            target='scope')
        elif ('project' in self.auth['scope'] and
              'domain' in self.auth['scope']):
            # both domain and project provided
            raise exception.ValidationError(attribute='project or domain',
                                            target='scope')

        if 'project' in self.auth['scope']:
            project_id = self.auth['scope']['project'].get('id', None)
            project_name = self.auth['scope']['project'].get('name', None)
            project_ref = None
            if project_id is None and project_name is None:
                raise exception.ValidationError(attribute='id or name',
                                                target='project')
            # TODO: for henrynash, need to check domain namespace here
            try:
                if project_name:
                    project_ref = self.identity_api.get_project_by_name(
                        context=self.context, tenant_name=project_name)
                else:
                    project_ref = self.identity_api.get_project(
                        context=self.context, project_id=project_id)
            except exception.ProjectNotFound as e:
                LOG.exception(e)
                raise exception.Unauthorized(e)
            # can't scope to a disabled project
            self._assert_project_is_enabled(project_ref)
            self._scope_data = (None, project_ref['id'])
        else:
            domain_id = self.auth['scope']['domain'].get('id', None)
            domain_name = self.auth['scope']['domain'].get('name', None)
            domain_ref = None
            if domain_id is None and domain_name is None:
                raise exception.ValidationError(attribute='id or name',
                                                target='domain')
            try:
                if domain_name:
                    domain_ref = self.identity_api.get_domain_by_name(
                        context=self.context, domain_name=domain_name)
                else:
                    domain_ref = self.identity_api.get_domain(
                        context=self.context, domain_id=domain_id)
            except exception.DomainNotFound as e:
                LOG.exception(e)
                raise exception.Unauthorized(e)
            # can't scope to a disabled domain
            self._assert_domain_is_enabled(domain_ref)
            self._scope_data = (domain_ref['id'], None)

    def _validate_auth_methods(self):
        # make sure auth methods are provided
        if 'methods' not in self.auth['authentication']:
            raise exception.ValidationError(attribute='methods',
                                            target='authentication')

        # make sure all the method data/payload are provided
        for method_name in self.get_method_names():
            if method_name not in self.auth['authentication']:
                raise exception.ValidationError(attribute=method_name,
                                                target='authentication')

        # make sure auth method is supported
        for method_name in self.get_method_names():
            if method_name not in CONF.auth.methods:
                raise exception.AuthMethodNotSupported()

    def _validate_and_normalize_auth_data(self):
        """ Make sure "auth" is valid. """
        # make sure "auth" exist
        if self.auth is None:
            raise exception.ValidationError(attribute='auth',
                                            target='request body')

        # validate auth methods
        self._validate_auth_methods()

        # validate and normalize scope
        self._validate_and_normalize_scope_data()

    def get_method_names(self):
        """ Returns the authentication method names.

        :returns: list of auth method names

        """
        return self.auth['authentication']['methods']

    def get_method_data(self, method):
        """ Get the auth method payload.

        :returns: auth method payload

        """
        if method not in self.auth['authentication']['methods']:
            raise AuthenticationMethodNotFound(method)
        return self.auth['authentication'][method]

    def get_scope(self):
        """ Get scope information.

        Verify and return the scoping information.

        :returns: (domain_id, project_id). If scope to a project,
                  (None, project_id) will be returned. If scope to a domain,
                  (domain_id, None) will be returned. If unscope,
                  (None, None) will be returned.

        """
        return self._scope_data

    def set_scope(self, domain_id=None, project_id=None):
        """ Set scope information. """
        self._scope_data = (domain_id, project_id)


class Auth(controller.V3Controller):
    def __init__(self, *args, **kw):
        super(Auth, self).__init__(*args, **kw)
        self.token_controllers_ref = token_controllers.Auth()

    #@controller.protected
    def authenticate_for_token(self, context, auth=None):
        """ Authenticate user and issue a token. """
        try:
            auth_info = AuthInfo(context, auth=auth)
            auth_context = {'extras': {}, 'method_names': []}
            self.authenticate(context, auth_info, auth_context)
            self._check_and_set_default_scoping(auth_info)
            (token_id, token_data) = \
                token_factory.create_token(context, auth_context, auth_info)
            return token_factory.render_token_data_response(token_id,
                                                            token_data)
        except (exception.Unauthorized,
                exception.AuthMethodNotSupported,
                exception.AdditionalAuthRequired) as e:
            raise e
        except Exception as ae:
            LOG.exception(ae)
            raise exception.Unauthorized(ae)

    def _check_and_set_default_scoping(self, auth_info):
        (domain_id, project_id) = auth_info.get_scope()
        if domain_id or project_id:
            # scope is specified
            return

        # fill in default_project_id if it is available
        try:
            user_ref = self.identity_api.get_user_by_name(
                context=context, user_name=username)
            default_project_id = user_ref.get('default_project_id', None)
            if default_project_id:
                auth_info.set_scope(None, default_project_id)
        except exception.UserNotFound as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)

    def _build_remote_user_auth_context(self, context, auth_info,
                                        auth_context):
        username = context['REMOTE_USER']
        try:
            user_ref = self.identity_api.get_user_by_name(
                context=context, user_name=username)
            auth_context['user_id'] = user_ref['id']
        except exception.UserNotFound as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)

    def authenticate(self, context, auth_info, auth_context):
        """ Authenticate user. """

        # user have been authenticated externally
        if 'REMOTE_USER' in context:
            return self._build_remote_user_auth_context(context,
                                                        auth_info,
                                                        auth_context)

        # need to aggregate the results in case two or more methods
        # are specified
        auth_response = {"methods": []}
        for method_name in auth_info.get_method_names():
            method = get_auth_method(method_name)
            resp = method.authenticate(context, auth_info, auth_context)
            if resp is not None:
                auth_response['methods'].append(method_name)
                auth_response[method_name] = resp

        if len(auth_response["methods"]) > 0:
            # authenticatin continuation required
            raise exception.AdditionalAuthRequired(auth_response)

    def check_token(self, context):
        token_id = context.get('subject_token_id', None)
        return self.token_controllers_ref.validate_token_head(context,
                                                              token_id)

    def revoke_token(self, context):
        token_id = context.get('subject_token_id', None)
        return self.token_controllers_ref.delete_token(context, token_id)

    def validate_token(self, context):
        token_id = context.get('subject_token_id', None)
        self.check_token(context)
        token_ref = self.token_api.get_token(context, token_id)
        return token_factory.recreate_token_data(context,
                                                 token_ref['token_data'],
                                                 token_ref['expires'])

    def revocation_list(self, context, auth=None):
        return self.token_controllers_ref.revocation_list(context, auth)
