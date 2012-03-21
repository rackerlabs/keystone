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

    def __call__(self, environ, start_response):
        identity = self._keystone_identity(environ)

        if identity:
            self.logger.debug('Using identity: %r' % (identity))
            environ['keystone.identity'] = identity
            environ['REMOTE_USER'] = identity.remote_user
            environ['swift.authorize'] = self.authorize
        else:
            self.logger.debug('Authorizing as anonymous')
            environ['swift.authorize'] = self.authorize_anonymous

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
        identity = req.environ['keystone.identity']

        try:
            part = swift_utils.split_path(req.path, 1, 4, True)
            version, account, container, obj = part
        except ValueError:
            return webob.exc.HTTPNotFound(request=req)

        # Give unconditional access to a user with the reseller_admin
        # role.
        if self.reseller_admin_role in identity.roles:
            msg = 'User %s has reseller admin authorizing'
            self.logger.debug(msg % identity.tenant_id)
            req.environ['swift_owner'] = True
            return

        # Check if a user tries to access an account that does not match their
        # token
        if not self._reseller_check(account, identity.tenant_id):
            log_msg = 'tenant mismatch: %s != %s' % (account,
                                                     identity.tenant_id)
            self.logger.debug(log_msg)
            return self.denied_response(req)

        # Check the roles the user is belonging to. If the user is
        # part of the role defined in the config variable
        # operator_roles (like admin) then it will be
        # promoted as an admin of the account/tenant.
        for role in self.operator_roles.split(','):
            role = role.strip()
            if role in identity.roles:
                log_msg = 'allow user with role %s as account admin' % (role)
                self.logger.debug(log_msg)
                req.environ['swift_owner'] = True
                return

        # If user is of the same name of the tenant then make owner of it.
        if self.is_admin and identity.user == identity.tenant_name:
            req.environ['swift_owner'] = True
            return

        referrers, roles = swift_acl.parse_acl(getattr(req, 'acl', None))

        authorized = self._authorize_unconfirmed_identity(req, obj, referrers,
                                                          roles)
        if authorized:
            return
        elif authorized is not None:
            return self.denied_response(req)

        # Allow ACL at individual user level (tenant:user format)
        if identity.tenant_user in roles:
            log_msg = 'user %s allowed in ACL authorizing'
            self.logger.debug(log_msg % identity.tenant_user)
            return

        # Check if we have the role in the userroles and allow it
        for user_role in identity.roles:
            if user_role in roles:
                log_msg = 'user %s allowed in ACL: %s authorizing'
                self.logger.debug(log_msg % (identity.tenant_user, user_role))
                return

        return self.denied_response(req)

    def authorize_anonymous(self, req):
        """
        Authorize an anonymous request.

        :returns: None if authorization is granted, an error page otherwise.
        """
        try:
            part = swift_utils.split_path(req.path, 1, 4, True)
            version, account, container, obj = part
        except ValueError:
            return webob.exc.HTTPNotFound(request=req)

        is_authoritative_authz = (account and
                                  account.startswith(self.reseller_prefix))
        if not is_authoritative_authz:
            return self.denied_response(req)

        referrers, roles = swift_acl.parse_acl(getattr(req, 'acl', None))
        authorized = self._authorize_unconfirmed_identity(req, obj, referrers,
                                                          roles)
        if not authorized:
            return self.denied_response(req)

    def _authorize_unconfirmed_identity(self, req, obj, referrers, roles):
        """
        Perform authorization for access that does not require a
        confirmed identity.

        :returns: A boolean if authorization is granted or denied.  None if
                  a determination could not be made.
        """
        # Allow container sync.
        if (req.environ.get('swift_sync_key')
            and req.environ['swift_sync_key'] ==
                req.headers.get('x-container-sync-key', None)
            and 'x-timestamp' in req.headers
            and (req.remote_addr in self.allowed_sync_hosts
                 or swift_utils.get_remote_client(req)
                 in self.allowed_sync_hosts)):
            log_msg = 'allowing proxy %s for container-sync' % req.remote_addr
            self.logger.debug(log_msg)
            return True

        # Check if referrer is allowed.
        if swift_acl.referrer_allowed(req.referer, referrers):
            if obj or '.rlistings' in roles:
                log_msg = 'authorizing %s via referer ACL' % req.referrer
                self.logger.debug(log_msg)
                return True
            return False

    def denied_response(self, req):
        """Deny WSGI Response.

        Returns a standard WSGI response callable with the status of 403 or 401
        depending on whether the REMOTE_USER is set or not.
        """
        if req.remote_user:
            return webob.exc.HTTPForbidden(request=req)
        else:
            return webob.exc.HTTPUnauthorized(request=req)


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
