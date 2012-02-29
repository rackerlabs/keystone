# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2012 OpenStack LLC
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

"""
TOKEN-BASED AUTH MIDDLEWARE

This WSGI component performs multiple jobs:

* it verifies that incoming client requests have valid tokens by verifying
  tokens with the auth service.
* it will reject unauthenticated requests UNLESS it is in 'delay_auth_decision'
  mode, which means the final decision is delegated to the downstream WSGI
  component (usually the OpenStack service)
* it will collect and forward identity information from a valid token
  such as user id, user name, tenant, roles, etc...

Refer to: http://keystone.openstack.org/

When possible both a name and ID is provided.  While the name is (usually)
human readable, it can change at any time.  Downstream services should use
the IDs.

Coming in from initial call from client or customer
---------------------------------------------------

HTTP_X_AUTH_TOKEN
    client token being passed in

HTTP_X_STORAGE_TOKEN (deprecated)
    client token being passed in (legacy Rackspace use) to support cloud files

What we add to the request for use by the OpenStack service
-----------------------------------------------------------

HTTP_X_IDENTITY_STATUS
    Confirmed or Invalid

HTTP_X_TENANT_NAME
    name of tenant if tenant is present

HTTP_X_TENANT_ID
    id of tenant if tenant is present

HTTP_X_USER
    name of user

HTTP_X_USER_ID
    id of user

HTTP_X_ROLE
    list of roles

"""

import httplib
import json
import logging

import webob
import webob.exc


logger = logging.getLogger('keystone.middleware.auth_token')


class InvalidUserToken(Exception):
    pass


class ServiceError(Exception):
    pass


class AuthProtocol(object):
    """Auth Middleware that handles authenticating client calls"""

    def __init__(self, app, conf):
        self.conf = conf
        self.app = app

        # delay_auth_decision means we still allow unauthenticated requests
        # through and we let the downstream service make the final decision
        self.delay_auth_decision = int(conf.get('delay_auth_decision', 0))

        # where to find the auth service (we use this to validate tokens)
        self.auth_host = conf.get('auth_host')
        self.auth_port = int(conf.get('auth_port'))

        auth_protocol = conf.get('auth_protocol', 'https')
        if auth_protocol == 'http':
            self.httplib_class = httplib.HTTPConnection
        else:
            self.httplib_class = httplib.HTTPSConnection

        default_auth_uri = '%s://%s:%s' % (auth_protocol,
                                           self.auth_host,
                                           self.auth_port)
        self.auth_uri = conf.get('auth_uri', default_auth_uri)

        # Credentials used to verify this component with the Auth service since
        # validating tokens is a privileged call
        self.admin_token = conf.get('admin_token')
        self.admin_user = conf.get('admin_user')
        self.admin_password = conf.get('admin_password')
        self.admin_tenant_name = conf.get('admin_tenant_name', 'admin')

    def __call__(self, env, start_response):
        """Handle incoming request

        Authenticate send downstream on success.
        Reject request if we can't authenticate.

        """
        try:
            user_token = self._get_user_token_from_header(env)
            token_info = self._validate_user_token(user_token)
            user_headers = self._build_user_headers(token_info)
            self._add_headers(user_headers, env)
            return self.app(env, start_response)

        except InvalidUserToken:
            logger.info("Invalid token")
            if self.delay_auth_decision:
                logger.info("Deferring reject to downstream")
                self._add_headers({'X_IDENTITY_STATUS': 'Invalid'}, env)
                return self.app(env, start_response)
            else:
                logger.info("Rejecting request")
                return self._reject_request(env, start_response)

        except ServiceError:
            logger.critical('Unable to obtain admin token')
            resp = webob.exc.HTTPServiceUnavailable()
            return resp(env, start_response)

    def _get_user_token_from_header(self, env):
        """Get token id from request

        :param env: wsgi request environment
        :return token id
        :raises InvalidUserToken if no token is provided in request

        """
        token = env.get('HTTP_X_AUTH_TOKEN', env.get('HTTP_X_STORAGE_TOKEN'))
        if token:
            return token
        else:
            raise InvalidUserToken('Unable to find token in headers')

    def _reject_request(self, env, start_response):
        """Redirect client to auth server

        :param env: wsgi request environment
        :param start_response: wsgi response callback
        :returns HTTPUnauthorized http response

        """
        headers = [('WWW-Authenticate', "Keystone uri='%s'" % self.auth_uri)]
        resp = webob.exc.HTTPUnauthorized('Authentication required', headers)
        return resp(env, start_response)

    def get_admin_token(self):
        """Return admin token, possibly fetching a new one

        :return admin token id
        :raise ServiceError when unable to retrieve token from keystone

        """
        if not self.admin_token:
            self.admin_token = self._request_admin_token()

        return self.admin_token

    def _json_request(self, method, path, body=None, additional_headers=None):
        """HTTP request helper used to make json requests

        :param method: http method
        :param path: relative request url
        :param body: dict to encode to json as request body. Optional.
        :param additional_headers: dict of additional headers to send with
                                   http request. Optional.
        :return (http response object, response body parsed as json)
        :raise ServerError when unable to communicate with keystone

        """
        conn = self.httplib_class(self.auth_host, self.auth_port)

        kwargs = {
            'headers': {
                'Content-type': 'application/json',
                'Accept': 'application/json',
            },
        }

        if additional_headers:
            kwargs['headers'].update(additional_headers)

        if body:
            kwargs['body'] = json.dumps(body)

        try:
            conn.request(method, path, **kwargs)
            response = conn.getresponse()
            body = response.read()
            data = json.loads(body)
        except Exception, e:
            logger.error('HTTP connection exception: %s' % e)
            raise ServiceError('Unable to make communicate with keystone')
        finally:
            conn.close()

        return response, data

    def _request_admin_token(self):
        """Retrieve new token as admin user from keystone

        :return token id upon success
        :raises ServerError when unable to communicate with keystone

        """
        params = {
            'auth': {
                'passwordCredentials': {
                    'username': self.admin_user,
                    'password': self.admin_password,
                },
                'tenantName': self.admin_tenant_name,
            }
        }

        response, data = self._json_request('POST',
                                            '/v2.0/tokens',
                                            body=params)

        try:
            token = data['access']['token']['id']
            assert token
            return token
        except (AssertionError, KeyError):
            raise ServiceError('invalid json response')

    def _validate_user_token(self, user_token, retry=True):
        """Authenticate user token with keystone

        :param user_token: user's token id
        :param retry: flag that forces the middleware to retry
                      user authentication when an indeterminate
                      response is received. Optional.
        :return token object received from keystone on success
        :raise InvalidUserToken if token is rejected
        :raise ServiceError if unable to authenticate token

        """
        headers = {'X-Auth-Token': self.get_admin_token()}
        response, data = self._json_request('GET',
                                            '/v2.0/tokens/%s' % user_token,
                                            additional_headers=headers)

        if response.status == 200:
            return data
        if response.status == 404:
            # FIXME(ja): I'm assuming the 404 status means that user_token is
            #            invalid - not that the admin_token is invalid
            raise InvalidUserToken('token authorization failed')
        if response.status == 401:
            logger.info('keystone rejected admin_token, resetting')
            self.admin_token = None
        else:
            logger.info('validating token http response code %s' %
                        response.status)
        if retry:
            logger.info('retrying validation')
            return self._validate_user_token(user_token, False)
        else:
            raise InvalidUserToken()

    def _build_user_headers(self, token_info):
        """Convert token object into headers

        Build headers that represent authenticated user:
         * X_TENANT_NAME: name of tenant if tenant is present
         * X_TENANT_ID: id of tenant if tenant is present
         * X_USER: name of user
         * X_USER_ID: id of user
         * X_ROLE: list of roles
         * X_IDENTITY_STATUS: Confirmed or Invalid

        Additional (deprecated) headers include:
         * X_TENANT: For legacy compatibility before we had ID and Name

        :param token_info: token object returned by keystone on authentication
        :raise InvalidUserToken when unable to parse token object

        """
        user = token_info['access']['user']
        token = token_info['access']['token']
        roles = [role['name'] for role in user.get('roles', [])]

        # FIXME(ja): I think we are checking in both places because:
        # tenant might not be returned, and there was a pre-release
        # that put tenant objects inside the user object?
        try:
            tenant_id = token['tenant']['id']
            tenant_name = token['tenant']['name']
        except:
            tenant_id = user.get('tenantId')
            tenant_name = user.get('tenantName')

        return {
            'X_IDENTITY_STATUS': 'Confirmed',
            'X_TENANT': tenant_name,
            'X_TENANT_NAME': tenant_name,
            'X_TENANT_ID': tenant_id,
            'X_USER': user['username'],
            'X_USER_ID': user['id'],
            'X_ROLE': ','.join(roles),
        }

    def _add_headers(self, values, env):
        """Add headers to environment"""
        for (k, v) in values.iteritems():
            env['HTTP_%s' % k] = v


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return AuthProtocol(app, conf)
    return auth_filter


def app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    return AuthProtocol(None, conf)
