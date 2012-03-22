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

    :param app: The next WSGI app in the pipeline
    :param conf: The dict of configuration values
    """
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = swift_utils.get_logger(conf, log_route='keystoneauth')
        self.reseller_prefix = conf.get('reseller_prefix', 'AUTH').strip()
        if self.reseller_prefix and self.reseller_prefix[-1] != '_':
            self.reseller_prefix += '_'
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
            IsResellerAdmin,
            TenantMismatch,
            IsAdmin,
            IsTenantOwner,
            AllowContainerSync,
            AllowReferrer,
            TenantUserInRoles,
            HasPermittedRole,
            ]
        self.anon_authz_checks = [
            IsAuthoritativeAuthz,
            AllowContainerSync,
            AllowReferrer,
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
            return Identity.from_headers(environ)

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

        acl_parts = swift_acl.parse_acl(getattr(req, 'acl', None))

        identity = req.environ.get('keystone.identity')
        if identity:
            authz_checks = self.authz_checks
        else:
            authz_checks = self.anon_authz_checks

        authz_args = (self, req, identity, path_parts, acl_parts)

        for authz_check in authz_checks:
            authorized = authz_check(*authz_args)()
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


class AuthzCheck(object):
    """
    Encapsulates an authorization check.

    """

    def __init__(self, auth, req, identity, path_parts, acl_parts):
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
        self.referrers, self.roles = acl_parts

    def __call__(self):
        """
        Perform an authorization check.

        :returns: A boolean if authorization is granted or denied,
                  None if a determination could not be made.
        """
        raise NotImplemented


class IsResellerAdmin(AuthzCheck):
    """
    Give unconditional access to a user with the reseller_admin role.

    """
    def __call__(self):
        if self.auth.reseller_admin_role in self.identity.roles:
            msg = 'User %s has reseller admin, authorizing'
            self.auth.logger.debug(msg % self.identity.tenant_id)
            self.req.environ['swift_owner'] = True
            return True


class TenantMismatch(AuthzCheck):
    """
    Check if a user tries to access an account that does not match
    their tenant_id.

    """
    def __call__(self):
        account = self.account
        identity = self.identity
        if not self.auth._reseller_check(account, identity.tenant_id):
            log_msg = 'tenant mismatch: %s != %s' % (account,
                                                     identity.tenant_id)
            self.auth.logger.debug(log_msg)
            return False


class IsAdmin(AuthzCheck):
    """
    Check the roles the user is belonging to. If the user is part of
    the role defined in the config variable operator_roles (like
    admin) then it will be promoted as an admin of the account/tenant.

    """
    def __call__(self):
        for role in self.auth.operator_roles.split(','):
            role = role.strip()
            if role in self.identity.roles:
                log_msg = 'allow user with role %s as account admin' % (role)
                self.auth.logger.debug(log_msg)
                self.req.environ['swift_owner'] = True
                return True


class IsTenantOwner(AuthzCheck):
    """
    If user is of the same name of the tenant then make owner of it.

    """
    def __call__(self):
        if (self.auth.is_admin and
            self.identity.user == self.identity.tenant_name):
            self.req.environ['swift_owner'] = True
            return True


class TenantUserInRoles(AuthzCheck):
    """
    Allow ACL at individual user level (tenant:user format)

    """
    def __call__(self):
        if self.identity.tenant_user in self.roles:
            log_msg = 'user %s allowed in ACL authorizing'
            self.auth.logger.debug(log_msg % self.identity.tenant_user)
            return True


class HasPermittedRole(AuthzCheck):
    """
    Check if we have the role in the userroles and allow it

    """
    def __call__(self):
        for user_role in self.identity.roles:
            if user_role in self.roles:
                log_msg = 'user %s allowed in ACL: %s authorizing' % (
                    self.identity.tenant_user, user_role)
                self.auth.logger.debug(log_msg)
                return True


class AllowContainerSync(AuthzCheck):
    """
    Allow container sync.

    """
    def __call__(self):
        req = self.req
        auth = self.auth
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
    def __call__(self):
        req = self.req
        if swift_acl.referrer_allowed(req.referer, self.referrers):
            if self.obj or '.rlistings' in self.roles:
                log_msg = 'authorizing %s via referer ACL' % req.referrer
                self.auth.logger.debug(log_msg)
                return True
            return False


class IsAuthoritativeAuthz(AuthzCheck):
    """
    Check if this authz service is authoritative for the account.

    """
    def __call__(self):
        account = self.account
        is_authoritative_authz = (
            account and account.startswith(self.auth.reseller_prefix))
        if not is_authoritative_authz:
            return False


class Identity(object):

    CONFIRMED = 'Confirmed'

    @classmethod
    def from_headers(cls, headers):
        header_ids = 'TENANT_ID TENANT_NAME USER ROLES'.split()
        args = [headers.get('HTTP_X_%s' % x, '') for x in header_ids]
        return cls(*args)

    def __init__(self, tenant_id, tenant_name, user, roles):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.user = user
        self.roles = roles.split(',')

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        return """
<Identity tenant_id="%s" tenant_name="%s" user="%s" roles="%s">
""".strip() % (self.tenant_id, self.tenant_name, self.user, self.str_roles)

    @property
    def remote_user(self):
        return (self.tenant_id, self.tenant_name)

    @property
    def str_roles(self):
        return ','.join(self.roles)

    @property
    def tenant_user(self):
        return '%s:%s' % (self.tenant_name, self.user)

    def to_headers(self, prefix='HTTP_X_'):
        headers = {
            'TENANT_ID': self.tenant_id,
            'TENANT_NAME': self.tenant_name,
            'USER': self.user,
            'ROLES': self.str_roles,
            }
        return dict(('%s%s' % (prefix, k), v) for k, v in headers.iteritems())


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return SwiftAuth(app, conf)
    return auth_filter
