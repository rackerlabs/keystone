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

# Copyright (c) 2012 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webob

from swift.common import utils as swift_utils
from swift.common.middleware import acl as swift_acl


class SwiftAuth(object):
    """Swift middleware to Keystone authorization system.

    In Swift's proxy-server.conf add this middleware to your pipeline::

        [pipeline:main]
        pipeline = catch_errors cache authtoken swiftauth proxy-server

    Make sure you have the authtoken middleware before the swiftauth
    middleware.  authtoken will take care of validating the user and
    swiftauth will authorize access.  If support is required for
    unvalidated users (as with anonymous access), authtoken will need
    to be configured with delay_auth_decision set to true.  See the
    documentation for more detail on how to configure the authtoken
    middleware.

    Set account auto creation to true::

        [app:proxy-server]
        account_autocreate = true

    And add a swift authorization filter section, such as::

        [filter:swiftauth]
        use = egg:keystone#swiftauth
        operator_roles = admin, swiftoperator
        is_admin = false

    This maps tenants to account in Swift.

    The user whose able to give ACL / create Containers permissions
    will be the one that are inside the operator_roles
    setting which by default includes the admin and the swiftoperator
    roles.

    The option is_admin if set to true will allow the
    username that has the same name as the account name to be the owner.

    Example: If we have the account called hellocorp with a user
    hellocorp that user will be admin on that account and can give ACL
    to all other users for hellocorp.

    If you need to have a different reseller_prefix to be able to
    mix different auth servers you can configure the option
    reseller_prefix in your swiftauth entry like this :

        reseller_prefix = NEWAUTH_

    Make sure you have a underscore at the end of your new
    reseller_prefix option.

    :param app: The next WSGI app in the pipeline
    :param conf: The dict of configuration values
    """
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = swift_utils.get_logger(conf, log_route='keystoneauth')
        self.reseller_prefix = conf.get('reseller_prefix', 'AUTH_').strip()
        self.operator_roles = conf.get('operator_roles',
                                       'admin, swiftoperator')
        self.reseller_admin_role = conf.get('reseller_admin_role',
                                            'ResellerAdmin')
        config_is_admin = conf.get('is_admin', "false").lower()
        self.is_admin = config_is_admin in ('true', 't', '1', 'on', 'yes', 'y')
        cfg_synchosts = conf.get('allowed_sync_hosts', '127.0.0.1')
        self.allowed_sync_hosts = [h.strip() for h in cfg_synchosts.split(',')
                                   if h.strip()]
        self.authz_checks = [
            IsResellerAdmin(),
            TenantMismatch(),
            IsAdmin(),
            IsTenantOwner(),
            AllowContainerSync(),
            AllowReferrer(),
            TenantUserInRoles(),
            HasPermittedRole(),
            ]
        self.anon_authz_checks = [
            IsAuthoritativeAuthz(),
            AllowContainerSync(),
            AllowReferrer(),
            ]

    def __call__(self, environ, start_response):
        identity = self._keystone_identity(environ)

        if identity:
            self.logger.debug('Using identity: %r' % (identity))
            environ['keystone.identity'] = identity
            environ['REMOTE_USER'] = identity.remote_user
        else:
            self.logger.debug('Authorizing as anonymous')

        environ['swift.authorize'] = self.authorize
        environ['swift.clean_acl'] = swift_acl.clean_acl

        return self.app(environ, start_response)

    def _keystone_identity(self, environ):
        """Extract the identity from the Keystone auth component."""
        if environ.get('HTTP_X_IDENTITY_STATUS') == Identity.CONFIRMED:
            return Identity.from_env(environ)

    def _get_account_for_tenant(self, tenant_id):
        return '%s%s' % (self.reseller_prefix, tenant_id)

    def _reseller_check(self, account, tenant_id):
        """Check reseller prefix."""
        return account == self._get_account_for_tenant(tenant_id)

    def authorize(self, req):
        """
        :returns: None if authorization is granted, an error page otherwise.

        """
        try:
            path_parts = swift_utils.split_path(req.path, 1, 4, True)
        except ValueError:
            return webob.exc.HTTPNotFound(request=req)

        identity = req.environ.get('keystone.identity')
        if identity:
            authz_checks = self.authz_checks
        else:
            authz_checks = self.anon_authz_checks

        authz_context = AuthzContext(self, req, identity, path_parts)

        for authz_check in authz_checks:
            authorized = authz_check(authz_context)
            if authorized:
                return
            elif authorized == False:
                break

        return self.denied_response(req)

    def denied_response(self, req):
        """Deny WSGI Response.

        Returns a standard WSGI response callable with the status of 403 or 401
        depending on whether the REMOTE_USER is set or not.
        """
        if req.remote_user:
            return webob.exc.HTTPForbidden(request=req)
        else:
            return webob.exc.HTTPUnauthorized(request=req)


class AuthzContext(object):
    """
    Encapsulates the data needed to perform an authorization check.

    """

    def __init__(self, auth, req, identity, path_parts):
        """
        :param auth: An instance of SwiftAuth
        :param req: The request to authorize
        :param identity: The validated identity
        :param path_parts: The parsed path (version, account, container, obj)
        :param acl_parts: The parsed acl (referrers, roles)

        """
        self.auth = auth
        self.req = req
        self.identity = identity
        self.version, self.account, self.container, self.obj = path_parts

    def _parse_acl(self):
        acl = getattr(self.req, 'acl', None)
        self._referrers, self._roles = swift_acl.parse_acl(acl)

    @property
    def referrers(self):
        if not hasattr(self, '_referrers'):
            self._parse_acl()
        return self._referrers

    @property
    def roles(self):
        if not hasattr(self, '_roles'):
            self._parse_acl()
        return self._roles


class AuthzCheck(object):
    """
    Encapsulates an authorization check.

    """

    def __call__(self, ctx):
        """
        Perform an authorization check.

        :param ctx: AuthzContext for the check
        :returns: A boolean if authorization is granted or denied,
                  None if a determination could not be made.
        """
        raise NotImplemented


class IsResellerAdmin(AuthzCheck):
    """
    Give unconditional access to a user with the reseller_admin role.

    """
    def __call__(self, ctx):
        if ctx.auth.reseller_admin_role in ctx.identity.roles:
            msg = 'User %s has reseller admin, authorizing'
            ctx.auth.logger.debug(msg % ctx.identity.tenant_id)
            ctx.req.environ['swift_owner'] = True
            return True


class TenantMismatch(AuthzCheck):
    """
    Check if a user tries to access an account that does not match
    their tenant_id.

    """
    def __call__(self, ctx):
        if not ctx.auth._reseller_check(ctx.account, ctx.identity.tenant_id):
            log_msg = 'tenant mismatch: %s != %s' % (ctx.account,
                                                     ctx.identity.tenant_id)
            ctx.auth.logger.debug(log_msg)
            return False


class IsAdmin(AuthzCheck):
    """
    Check the roles the user is belonging to. If the user is part of
    the role defined in the config variable operator_roles (like
    admin) then it will be promoted as an admin of the account/tenant.

    """
    def __call__(self, ctx):
        for role in ctx.auth.operator_roles.split(','):
            role = role.strip()
            if role in ctx.identity.roles:
                log_msg = 'allow user with role %s as account admin' % role
                ctx.auth.logger.debug(log_msg)
                ctx.req.environ['swift_owner'] = True
                return True


class IsTenantOwner(AuthzCheck):
    """
    If user is of the same name of the tenant then make owner of it.

    """
    def __call__(self, ctx):
        if (ctx.auth.is_admin and
            ctx.identity.user_name == ctx.identity.tenant_name):
            ctx.req.environ['swift_owner'] = True
            return True


class TenantUserInRoles(AuthzCheck):
    """
    Allow ACL at individual user level (tenant:user format)

    """
    def __call__(self, ctx):
        if ctx.identity.tenant_user in ctx.roles:
            log_msg = 'user %s allowed in ACL authorizing'
            ctx.auth.logger.debug(log_msg % ctx.identity.tenant_user)
            return True


class HasPermittedRole(AuthzCheck):
    """
    Check if we have the role in the userroles and allow it

    """
    def __call__(self, ctx):
        for user_role in ctx.identity.roles:
            if user_role in ctx.roles:
                log_msg = 'user %s allowed in ACL: %s authorizing' % (
                    ctx.identity.tenant_user, user_role)
                ctx.auth.logger.debug(log_msg)
                return True


class AllowContainerSync(AuthzCheck):
    """
    Allow container sync.

    """
    def __call__(self, ctx):
        req = ctx.req
        auth = ctx.auth
        if (req.environ.get('swift_sync_key')
            and req.environ['swift_sync_key'] ==
                req.headers.get('x-container-sync-key', None)
            and 'x-timestamp' in req.headers
            and (req.remote_addr in auth.allowed_sync_hosts
                 or swift_utils.get_remote_client(req)
                 in auth.allowed_sync_hosts)):
            log_msg = 'allowing proxy %s for container-sync' % req.remote_addr
            auth.logger.debug(log_msg)
            return True


class AllowReferrer(AuthzCheck):
    """
    Check if referrer is allowed.

    """
    def __call__(self, ctx):
        if swift_acl.referrer_allowed(ctx.req.referer, ctx.referrers):
            if ctx.obj or '.rlistings' in ctx.roles:
                log_msg = 'authorizing %s via referer ACL' % ctx.req.referrer
                ctx.auth.logger.debug(log_msg)
                return True
            return False


class IsAuthoritativeAuthz(AuthzCheck):
    """
    Check if this authz service is authoritative for the account.

    """
    def __call__(self, ctx):
        if not (ctx.account and
                ctx.account.startswith(ctx.auth.reseller_prefix)):
            return False


class Identity(object):

    CONFIRMED = 'Confirmed'

    ENV_PREFIX = 'HTTP_X_'

    HEADER_PREFIX = 'X_'

    @classmethod
    def _load(cls, value_map, key_prefix):
        env_ids = 'TENANT_ID TENANT_NAME USER_ID USER_NAME ROLES'.split()
        args = [value_map.get('%s%s' % (key_prefix, x), '') for x in env_ids]
        return cls(*args)

    @classmethod
    def from_env(cls, env):
        return cls._load(env, cls.ENV_PREFIX)

    @classmethod
    def from_headers(cls, env):
        return cls._load(env, cls.HEADER_PREFIX)

    def __init__(self, tenant_id, tenant_name, user_id, user_name, roles):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.user_id = user_id
        self.user_name = user_name
        self.roles = roles.split(',')

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        return ('<Identity tenant_id="%s" tenant_name="%s" '
                'user_id="%s" user_name="%s" roles="%s">' %
                (self.tenant_id, self.tenant_name, self.user_id,
                 self.user_name, self.str_roles))

    def _dump(self, key_prefix):
        value_map = {
            'TENANT_ID': self.tenant_id,
            'TENANT_NAME': self.tenant_name,
            'USER_ID': self.user_id,
            'USER_NAME': self.user_name,
            'ROLES': self.str_roles,
            }
        return dict(('%s%s' % (key_prefix, k), v)
                    for k, v in value_map.iteritems())

    @property
    def remote_user(self):
        return (self.tenant_id, self.tenant_name)

    @property
    def str_roles(self):
        return ','.join(self.roles)

    @property
    def tenant_user(self):
        return '%s:%s' % (self.tenant_name, self.user_name)

    def to_env(self):
        return self._dump(self.ENV_PREFIX)

    def to_headers(self):
        return self._dump(self.HEADER_PREFIX)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return SwiftAuth(app, conf)
    return auth_filter
