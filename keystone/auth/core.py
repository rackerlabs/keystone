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

from functools import partial
import sys

from oslo_log import log
import six
import stevedore

from keystone.common import driver_hints
from keystone.common import provider_api
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone.federation import constants
from keystone.i18n import _
from keystone.identity.backends import resource_options as ro


LOG = log.getLogger(__name__)
CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs

# registry of authentication methods
AUTH_METHODS = {}
AUTH_PLUGINS_LOADED = False


def _get_auth_driver_manager(namespace, plugin_name):
    return stevedore.DriverManager(namespace, plugin_name, invoke_on_load=True)


def _check_and_set_default_scoping(auth_info, auth_context):
    (domain_id, project_id, trust, unscoped, system) = (
        auth_info.get_scope()
    )
    if trust:
        project_id = trust['project_id']
    if system or domain_id or project_id or trust:
        # scope is specified
        return

    # Skip scoping when unscoped federated token is being issued
    if constants.IDENTITY_PROVIDER in auth_context:
        return

    # Do not scope if request is for explicitly unscoped token
    if unscoped is not None:
        return

    # fill in default_project_id if it is available
    try:
        user_ref = PROVIDERS.identity_api.get_user(auth_context['user_id'])
    except exception.UserNotFound as e:
        LOG.warning(six.text_type(e))
        raise exception.Unauthorized(e)

    default_project_id = user_ref.get('default_project_id')
    if not default_project_id:
        # User has no default project. He shall get an unscoped token.
        return

    # make sure user's default project is legit before scoping to it
    try:
        default_project_ref = PROVIDERS.resource_api.get_project(
            default_project_id)
        default_project_domain_ref = PROVIDERS.resource_api.get_domain(
            default_project_ref['domain_id'])
        if (default_project_ref.get('enabled', True) and
                default_project_domain_ref.get('enabled', True)):
            if PROVIDERS.assignment_api.get_roles_for_user_and_project(
                    user_ref['id'], default_project_id):
                auth_info.set_scope(project_id=default_project_id)
            else:
                msg = ("User %(user_id)s doesn't have access to"
                       " default project %(project_id)s. The token"
                       " will be unscoped rather than scoped to the"
                       " project.")
                LOG.debug(msg,
                          {'user_id': user_ref['id'],
                           'project_id': default_project_id})
        else:
            msg = ("User %(user_id)s's default project %(project_id)s"
                   " is disabled. The token will be unscoped rather"
                   " than scoped to the project.")
            LOG.debug(msg,
                      {'user_id': user_ref['id'],
                       'project_id': default_project_id})
    except (exception.ProjectNotFound, exception.DomainNotFound):
        # default project or default project domain doesn't exist,
        # will issue unscoped token instead
        msg = ("User %(user_id)s's default project %(project_id)s not"
               " found. The token will be unscoped rather than"
               " scoped to the project.")
        LOG.debug(msg, {'user_id': user_ref['id'],
                        'project_id': default_project_id})


def load_auth_method(method):
    plugin_name = CONF.auth.get(method) or 'default'
    namespace = 'keystone.auth.%s' % method
    driver_manager = _get_auth_driver_manager(namespace, plugin_name)
    return driver_manager.driver


def load_auth_methods():
    global AUTH_PLUGINS_LOADED

    if AUTH_PLUGINS_LOADED:
        # Only try and load methods a single time.
        return
    # config.setup_authentication should be idempotent, call it to ensure we
    # have setup all the appropriate configuration options we may need.
    keystone.conf.auth.setup_authentication()
    for plugin in set(CONF.auth.methods):
        AUTH_METHODS[plugin] = load_auth_method(plugin)
    AUTH_PLUGINS_LOADED = True


def get_auth_method(method_name):
    global AUTH_METHODS
    if method_name not in AUTH_METHODS:
        raise exception.AuthMethodNotSupported()
    return AUTH_METHODS[method_name]


# NOTE(morgan): this is an intermediate object that encapsulates the auth
# controller methods "authenticate_for_token" and "authenticate" for purposes
# of migrating to flask. This is needed as federation work flows lean on the
# authenticate_for_token method directly.
class AuthHelper(object):

    @staticmethod
    def authenticate(request, auth_info, auth_context):
        """Authenticate user."""
        # NOTE(notmorgan): This is not super pythonic, but we lean on the
        # __setitem__ method in auth_context to handle edge cases and security
        # of the attributes set by the plugins. This check to ensure
        # `auth_context` is an instance of AuthContext is extra insurance and
        # will prevent regressions.

        if not isinstance(auth_context, AuthContext):
            LOG.error(
                '`auth_context` passed to the Auth controller '
                '`authenticate` method is not of type '
                '`keystone.auth.core.AuthContext`. For security '
                'purposes this is required. This is likely a programming '
                'error. Received object of type `%s`', type(auth_context))
            raise exception.Unauthorized(
                _('Cannot Authenticate due to internal error.'))
        # The 'external' method allows any 'REMOTE_USER' based authentication
        # In some cases the server can set REMOTE_USER as '' instead of
        # dropping it, so this must be filtered out
        if request.remote_user:
            try:
                external = get_auth_method('external')
                resp = external.authenticate(request,
                                             auth_info)
                if resp and resp.status:
                    # NOTE(notmorgan): ``external`` plugin cannot be multi-step
                    # it is either a plain success/fail.
                    auth_context.setdefault(
                        'method_names', []).insert(0, 'external')
                    # NOTE(notmorgan): All updates to auth_context is handled
                    # here in the .authenticate method.
                    auth_context.update(resp.response_data or {})

            except exception.AuthMethodNotSupported:
                # This will happen there is no 'external' plugin registered
                # and the container is performing authentication.
                # The 'kerberos'  and 'saml' methods will be used this way.
                # In those cases, it is correct to not register an
                # 'external' plugin;  if there is both an 'external' and a
                # 'kerberos' plugin, it would run the check on identity twice.
                LOG.debug("No 'external' plugin is registered.")
            except exception.Unauthorized:
                # If external fails then continue and attempt to determine
                # user identity using remaining auth methods
                LOG.debug("Authorization failed for 'external' auth method.")

        # need to aggregate the results in case two or more methods
        # are specified
        auth_response = {'methods': []}
        for method_name in auth_info.get_method_names():
            method = get_auth_method(method_name)
            resp = method.authenticate(request,
                                       auth_info.get_method_data(method_name))
            if resp:
                if resp.status:
                    auth_context.setdefault(
                        'method_names', []).insert(0, method_name)
                    # NOTE(notmorgan): All updates to auth_context is handled
                    # here in the .authenticate method. If the auth attempt was
                    # not successful do not update the auth_context
                    resp_method_names = resp.response_data.pop(
                        'method_names', [])
                    auth_context['method_names'].extend(resp_method_names)
                    auth_context.update(resp.response_data or {})
                elif resp.response_body:
                    auth_response['methods'].append(method_name)
                    auth_response[method_name] = resp.response_body

        if auth_response["methods"]:
            # authentication continuation required
            raise exception.AdditionalAuthRequired(auth_response)

        if 'user_id' not in auth_context:
            msg = _('User not found by auth plugin; authentication failed')
            LOG.warning(msg)
            raise exception.Unauthorized(msg)

    @classmethod
    def auth_for_token_webob(cls, request, auth=None):
        """Authenticate user and issue a token."""
        include_catalog = 'nocatalog' not in request.params

        try:
            auth_info = AuthInfo.create(auth=auth)
            auth_context = AuthContext(extras={},
                                       method_names=[],
                                       bind={})
            cls.authenticate(request, auth_info, auth_context)
            if auth_context.get('access_token_id'):
                auth_info.set_scope(None, auth_context['project_id'], None)
            _check_and_set_default_scoping(auth_info, auth_context)
            (domain_id, project_id, trust, unscoped, system) = (
                auth_info.get_scope()
            )

            # NOTE(notmorgan): only methods that actually run and succeed will
            # be in the auth_context['method_names'] list. Do not blindly take
            # the values from auth_info, look at the authoritative values. Make
            # sure the set is unique.
            method_names_set = set(auth_context.get('method_names', []))
            method_names = list(method_names_set)

            app_cred_id = None
            if 'application_credential' in method_names:
                token_auth = auth_info.auth['identity']
                app_cred_id = token_auth['application_credential']['id']

            # Do MFA Rule Validation for the user
            if not UserMFARulesValidator.check_auth_methods_against_rules(
                    auth_context['user_id'], method_names_set):
                raise exception.InsufficientAuthMethods(
                    user_id=auth_context['user_id'],
                    methods='[%s]' % ','.join(auth_info.get_method_names()))

            expires_at = auth_context.get('expires_at')
            token_audit_id = auth_context.get('audit_id')

            is_domain = auth_context.get('is_domain')
            (token_id, token_data) = PROVIDERS.token_provider_api.issue_token(
                auth_context['user_id'], method_names, expires_at=expires_at,
                system=system, project_id=project_id,
                is_domain=is_domain, domain_id=domain_id,
                auth_context=auth_context, trust=trust,
                app_cred_id=app_cred_id, include_catalog=include_catalog,
                parent_audit_id=token_audit_id)

            # NOTE(wanghong): We consume a trust use only when we are using
            # trusts and have successfully issued a token.
            if trust:
                PROVIDERS.trust_api.consume_use(trust['id'])

            return token_id, token_data
        except exception.TrustNotFound as e:
            LOG.warning(six.text_type(e))
            raise exception.Unauthorized(e)


class AuthContext(dict):
    """Retrofitting auth_context to reconcile identity attributes.

    The identity attributes must not have conflicting values among the
    auth plug-ins. The only exception is `expires_at`, which is set to its
    earliest value.

    """

    # identity attributes need to be reconciled among the auth plugins
    IDENTITY_ATTRIBUTES = frozenset(['user_id', 'project_id',
                                     'access_token_id', 'domain_id',
                                     'expires_at'])

    def __setitem__(self, key, val):
        """Override __setitem__ to prevent conflicting values."""
        if key in self.IDENTITY_ATTRIBUTES and key in self:
            existing_val = self[key]
            if key == 'expires_at':
                # special treatment for 'expires_at', we are going to take
                # the earliest expiration instead.
                if existing_val != val:
                    LOG.info('"expires_at" has conflicting values '
                             '%(existing)s and %(new)s.  Will use the '
                             'earliest value.',
                             {'existing': existing_val, 'new': val})
                if existing_val is None or val is None:
                    val = existing_val or val
                else:
                    val = min(existing_val, val)
            elif existing_val != val:
                msg = _('Unable to reconcile identity attribute %(attribute)s '
                        'as it has conflicting values %(new)s and %(old)s') % (
                            {'attribute': key,
                             'new': val,
                             'old': existing_val})
                raise exception.Unauthorized(msg)
        return super(AuthContext, self).__setitem__(key, val)

    def update(self, E=None, **F):
        """Override update to prevent conflicting values."""
        # NOTE(notmorgan): This will not be nearly as performant as the
        # use of the built-in "update" method on the dict, however, the
        # volume of data being changed here is very minimal in most cases
        # and should not see a significant impact by iterating instead of
        # explicit setting of values.
        update_dicts = (E or {}, F or {})
        for d in update_dicts:
            for key, val in d.items():
                self[key] = val


class AuthInfo(provider_api.ProviderAPIMixin, object):
    """Encapsulation of "auth" request."""

    @staticmethod
    def create(auth=None, scope_only=False):
        auth_info = AuthInfo(auth=auth)
        auth_info._validate_and_normalize_auth_data(scope_only)
        return auth_info

    def __init__(self, auth=None):
        self.auth = auth
        self._scope_data = (None, None, None, None, None)
        # self._scope_data is
        # (domain_id, project_id, trust_ref, unscoped, system)
        # project scope: (None, project_id, None, None, None)
        # domain scope: (domain_id, None, None, None, None)
        # trust scope: (None, None, trust_ref, None, None)
        # unscoped: (None, None, None, 'unscoped', None)
        # system: (None, None, None, None, 'all')

    def _assert_project_is_enabled(self, project_ref):
        # ensure the project is enabled
        try:
            PROVIDERS.resource_api.assert_project_enabled(
                project_id=project_ref['id'],
                project=project_ref)
        except AssertionError as e:
            LOG.warning(six.text_type(e))
            six.reraise(exception.Unauthorized, exception.Unauthorized(e),
                        sys.exc_info()[2])

    def _assert_domain_is_enabled(self, domain_ref):
        try:
            PROVIDERS.resource_api.assert_domain_enabled(
                domain_id=domain_ref['id'],
                domain=domain_ref)
        except AssertionError as e:
            LOG.warning(six.text_type(e))
            six.reraise(exception.Unauthorized, exception.Unauthorized(e),
                        sys.exc_info()[2])

    def _lookup_domain(self, domain_info):
        domain_id = domain_info.get('id')
        domain_name = domain_info.get('name')
        try:
            if domain_name:
                if (CONF.resource.domain_name_url_safe == 'strict' and
                        utils.is_not_url_safe(domain_name)):
                    msg = _('Domain name cannot contain reserved characters.')
                    LOG.warning(msg)
                    raise exception.Unauthorized(message=msg)
                domain_ref = PROVIDERS.resource_api.get_domain_by_name(
                    domain_name)
            else:
                domain_ref = PROVIDERS.resource_api.get_domain(domain_id)
        except exception.DomainNotFound as e:
            LOG.warning(six.text_type(e))
            raise exception.Unauthorized(e)
        self._assert_domain_is_enabled(domain_ref)
        return domain_ref

    def _lookup_project(self, project_info):
        project_id = project_info.get('id')
        project_name = project_info.get('name')
        try:
            if project_name:
                if (CONF.resource.project_name_url_safe == 'strict' and
                        utils.is_not_url_safe(project_name)):
                    msg = _('Project name cannot contain reserved characters.')
                    LOG.warning(msg)
                    raise exception.Unauthorized(message=msg)
                if 'domain' not in project_info:
                    raise exception.ValidationError(attribute='domain',
                                                    target='project')
                domain_ref = self._lookup_domain(project_info['domain'])
                project_ref = PROVIDERS.resource_api.get_project_by_name(
                    project_name, domain_ref['id'])
            else:
                project_ref = PROVIDERS.resource_api.get_project(project_id)
                # NOTE(morganfainberg): The _lookup_domain method will raise
                # exception.Unauthorized if the domain isn't found or is
                # disabled.
                self._lookup_domain({'id': project_ref['domain_id']})
        except exception.ProjectNotFound as e:
            LOG.warning(six.text_type(e))
            raise exception.Unauthorized(e)
        self._assert_project_is_enabled(project_ref)
        return project_ref

    def _lookup_trust(self, trust_info):
        trust_id = trust_info.get('id')
        if not trust_id:
            raise exception.ValidationError(attribute='trust_id',
                                            target='trust')
        trust = PROVIDERS.trust_api.get_trust(trust_id)
        return trust

    def _lookup_app_cred(self, app_cred_info):
        app_cred_id = app_cred_info.get('id')
        if app_cred_id:
            get_app_cred = partial(
                PROVIDERS.application_credential_api.get_application_credential
            )
            return get_app_cred(app_cred_id)
        name = app_cred_info.get('name')
        if not name:
            raise exception.ValidationError(attribute='name or ID',
                                            target='application credential')
        user = app_cred_info.get('user')
        if not user:
            raise exception.ValidationError(attribute='user',
                                            target='application credential')
        user_id = user.get('id')
        if not user_id:
            if 'domain' not in user:
                raise exception.ValidationError(attribute='domain',
                                                target='user')
            domain_ref = self._lookup_domain(user['domain'])
            user_id = PROVIDERS.identity_api.get_user_by_name(
                user['name'], domain_ref['id'])['id']
        hints = driver_hints.Hints()
        hints.add_filter('name', name)
        app_cred_api = PROVIDERS.application_credential_api
        app_creds = app_cred_api.list_application_credentials(
            user_id, hints)
        if len(app_creds) != 1:
            message = "Could not find application credential: %s" % name
            LOG.warning(six.text_type(message))
            raise exception.Unauthorized(message)
        return app_creds[0]

    def _set_scope_from_app_cred(self, app_cred_info):
        app_cred_ref = self._lookup_app_cred(app_cred_info)
        self._scope_data = (None, app_cred_ref['project_id'], None, None, None)
        return

    def _validate_and_normalize_scope_data(self):
        """Validate and normalize scope data."""
        if 'identity' in self.auth:
            if 'application_credential' in self.auth['identity']['methods']:
                # Application credentials can't choose their own scope
                if 'scope' in self.auth:
                    detail = "Application credentials cannot request a scope."
                    raise exception.ApplicationCredentialAuthError(
                        detail=detail)
                self._set_scope_from_app_cred(
                    self.auth['identity']['application_credential'])
                return
        if 'scope' not in self.auth:
            return
        if sum(['project' in self.auth['scope'],
                'domain' in self.auth['scope'],
                'unscoped' in self.auth['scope'],
                'system' in self.auth['scope'],
                'OS-TRUST:trust' in self.auth['scope']]) != 1:
            msg = 'system, project, domain, OS-TRUST:trust or unscoped'
            raise exception.ValidationError(attribute=msg, target='scope')
        if 'system' in self.auth['scope']:
            self._scope_data = (None, None, None, None, 'all')
            return
        if 'unscoped' in self.auth['scope']:
            self._scope_data = (None, None, None, 'unscoped', None)
            return
        if 'project' in self.auth['scope']:
            project_ref = self._lookup_project(self.auth['scope']['project'])
            self._scope_data = (None, project_ref['id'], None, None, None)
        elif 'domain' in self.auth['scope']:
            domain_ref = self._lookup_domain(self.auth['scope']['domain'])
            self._scope_data = (domain_ref['id'], None, None, None, None)
        elif 'OS-TRUST:trust' in self.auth['scope']:
            trust_ref = self._lookup_trust(
                self.auth['scope']['OS-TRUST:trust'])
            # TODO(ayoung): when trusts support domains, fill in domain data
            if trust_ref.get('project_id') is not None:
                project_ref = self._lookup_project(
                    {'id': trust_ref['project_id']})
                self._scope_data = (
                    None, project_ref['id'], trust_ref, None, None
                )

            else:
                self._scope_data = (None, None, trust_ref, None, None)

    def _validate_auth_methods(self):
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
        """Return the identity method names.

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

        :returns: (domain_id, project_id, trust_ref, unscoped, system).
                   If scope to a project, (None, project_id, None, None, None)
                   will be returned.
                   If scoped to a domain, (domain_id, None, None, None, None)
                   will be returned.
                   If scoped to a trust,
                   (None, project_id, trust_ref, None, None),
                   Will be returned, where the project_id comes from the
                   trust definition.
                   If unscoped, (None, None, None, 'unscoped', None) will be
                   returned.
                   If system_scoped, (None, None, None, None, 'all') will be
                   returned.

        """
        return self._scope_data

    def set_scope(self, domain_id=None, project_id=None, trust=None,
                  unscoped=None, system=None):
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
        if system and project_id:
            msg = _('Scoping to both project and system is not allowed')
            raise ValueError(msg)
        if system and domain_id:
            msg = _('Scoping to both domain and system is not allowed')
            raise ValueError(msg)
        self._scope_data = (domain_id, project_id, trust, unscoped, system)


class UserMFARulesValidator(object):
    """Helper object that can validate the MFA Rules."""

    @staticmethod
    def _auth_methods():
        if AUTH_PLUGINS_LOADED:
            return set(AUTH_METHODS.keys())
        raise RuntimeError(_('Auth Method Plugins are not loaded.'))

    @classmethod
    def check_auth_methods_against_rules(cls, user_id, auth_methods):
        """Validate the MFA rules against the successful auth methods.

        :param user_id: The user's ID (uuid).
        :type user_id: str
        :param auth_methods: List of methods that were used for auth
        :type auth_methods: set
        :returns: Boolean, ``True`` means rules match and auth may proceed,
                  ``False`` means rules do not match.
        """
        user_ref = PROVIDERS.identity_api.get_user(user_id)
        mfa_rules = user_ref['options'].get(ro.MFA_RULES_OPT.option_name, [])
        mfa_rules_enabled = user_ref['options'].get(
            ro.MFA_ENABLED_OPT.option_name, True)
        rules = cls._parse_rule_structure(mfa_rules, user_ref['id'])

        if not rules or not mfa_rules_enabled:
            # return quickly if the rules are disabled for the user or not set
            LOG.debug('MFA Rules not processed for user `%(user_id)s`. '
                      'Rule list: `%(rules)s` (Enabled: `%(enabled)s`).',
                      {'user_id': user_id,
                       'rules': mfa_rules,
                       'enabled': mfa_rules_enabled})
            return True

        for r in rules:
            # NOTE(notmorgan): We only check against the actually loaded
            # auth methods meaning that the keystone administrator may
            # disable an auth method, and a rule will still pass making it
            # impossible to accidently lock-out a subset of users with a
            # bad keystone.conf
            r_set = set(r).intersection(cls._auth_methods())
            if set(auth_methods).issuperset(r_set):
                # Rule Matches no need to continue, return here.
                LOG.debug('Auth methods for user `%(user_id)s`, `%(methods)s` '
                          'matched MFA rule `%(rule)s`. Loaded '
                          'auth_methods: `%(loaded)s`',
                          {'user_id': user_id,
                           'rule': list(r_set),
                           'methods': auth_methods,
                           'loaded': cls._auth_methods()})
                return True

        LOG.debug('Auth methods for user `%(user_id)s`, `%(methods)s` did not '
                  'match a MFA rule in `%(rules)s`.',
                  {'user_id': user_id,
                   'methods': auth_methods,
                   'rules': rules})
        return False

    @staticmethod
    def _parse_rule_structure(rules, user_id):
        """Validate and parse the rule data structure.

        Rule sets must be in the form of list of lists. The lists may not
        have duplicates and must not be empty. The top-level list may be empty
        indicating that no rules exist.

        :param rules: The list of rules from the user_ref
        :type rules: list
        :param user_id: the user_id, used for logging purposes
        :type user_id: str
        :returns: list of list, duplicates are stripped
        """
        # NOTE(notmorgan): Most of this is done at the API request validation
        # and in the storage layer, it makes sense to also validate here and
        # ensure the data returned from the DB is sane, This will not raise
        # any exceptions, but just produce a usable set of data for rules
        # processing.
        rule_set = []
        if not isinstance(rules, list):
            LOG.error('Corrupt rule data structure for user %(user_id)s, '
                      'no rules loaded.',
                      {'user_id': user_id})
            # Corrupt Data means no rules. Auth success > MFA rules in this
            # case.
            return rule_set
        elif not rules:
            # Exit early, nothing to do here.
            return rule_set

        for r_list in rules:
            if not isinstance(r_list, list):
                # Rule was not a list, it is invalid, drop the rule from
                # being considered.
                LOG.info('Ignoring Rule %(type)r; rule must be a list of '
                         'strings.',
                         {'type': type(r_list)})
                continue

            if r_list:
                # No empty rules are allowed.
                _ok_rule = True
                for item in r_list:
                    if not isinstance(item, six.string_types):
                        # Rules may only contain strings for method names
                        # Reject a rule with non-string values
                        LOG.info('Ignoring Rule %(rule)r; rule contains '
                                 'non-string values.',
                                 {'rule': r_list})
                        # Rule is known to be bad, drop it from consideration.
                        _ok_rule = False
                        break
                # NOTE(notmorgan): No FOR/ELSE used here! Though it could be
                # done and avoid the use of _ok_rule. This is a note for
                # future developers to avoid using for/else and as an example
                # of how to implement it that is readable and maintainable.
                if _ok_rule:
                    # Unique the r_list and cast back to a list and then append
                    # as we know the rule is ok (matches our requirements).
                    # This is outside the for loop, as the for loop is
                    # only used to validate the elements in the list. The
                    # This de-dupe should never be needed, but we are being
                    # extra careful at all levels of validation for the MFA
                    # rules.
                    r_list = list(set(r_list))
                    rule_set.append(r_list)

        return rule_set
