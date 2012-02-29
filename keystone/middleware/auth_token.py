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
  such as user name etc...

Refer to: http://wiki.openstack.org/openstack-authn


HEADERS
-------

* Headers starting with HTTP\_ is a standard http header
* Headers starting with HTTP_X is an extended http header

Coming in from initial call from client or customer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

HTTP_X_AUTH_TOKEN
    the client token being passed in

HTTP_X_STORAGE_TOKEN
    the client token being passed in (legacy Rackspace use) to support
    cloud files

Used for communication between components
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

www-authenticate
    only used if this component is being used remotely

HTTP_AUTHORIZATION
    basic auth password used to validate the connection

What we add to the request for use by the OpenStack service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

HTTP_X_AUTHORIZATION
    the client identity being passed in

"""
import httplib
import json
import os

import eventlet
from eventlet import wsgi
from paste import deploy
from urlparse import urlparse
import webob
import webob.exc

from keystone.common.bufferedhttp import http_connect_raw as http_connect

PROTOCOL_NAME = 'Token Authentication'


class AuthProtocol(object):
    """Auth Middleware that handles authenticating client calls"""

    def _init_protocol_common(self, app, conf):
        """ Common initialization code"""
        print 'Starting the %s component' % PROTOCOL_NAME

        self.conf = conf
        self.app = app
        #if app is set, then we are in a WSGI pipeline and requests get passed
        # on to app. If it is not set, this component should forward requests

        # where to find the OpenStack service (if not in local WSGI chain)
        # these settings are only used if this component is acting as a proxy
        # and the OpenSTack service is running remotely
        self.service_protocol = conf.get('service_protocol', 'https')
        self.service_host = conf.get('service_host')
        self.service_port = int(conf.get('service_port'))
        self.service_url = '%s://%s:%s' % (self.service_protocol,
                                           self.service_host,
                                           self.service_port)
        # used to verify this component with the OpenStack service or PAPIAuth
        self.service_pass = conf.get('service_pass')

        # delay_auth_decision means we still allow unauthenticated requests
        # through and we let the downstream service make the final decision
        self.delay_auth_decision = int(conf.get('delay_auth_decision', 0))

    def _init_protocol(self, conf):
        """ Protocol specific initialization """

        # where to find the auth service (we use this to validate tokens)
        self.auth_host = conf.get('auth_host')
        self.auth_port = int(conf.get('auth_port'))
        self.auth_protocol = conf.get('auth_protocol', 'https')

        # where to tell clients to find the auth service (default to url
        # constructed based on endpoint we have for the service to use)
        self.auth_location = conf.get('auth_uri',
                                      '%s://%s:%s' % (self.auth_protocol,
                                                      self.auth_host,
                                                      self.auth_port))

        # Credentials used to verify this component with the Auth service since
        # validating tokens is a privileged call
        self.admin_token = conf.get('admin_token')
        self.admin_user = conf.get('admin_user')
        self.admin_password = conf.get('admin_password')
        self.admin_tenant_name = conf.get('admin_tenant_name', 'admin')

    def __init__(self, app, conf):
        """ Common initialization code """

        #TODO(ziad): maybe we refactor this into a superclass
        self._init_protocol_common(app, conf)  # Applies to all protocols
        self._init_protocol(conf)  # Specific to this protocol

    def __call__(self, env, start_response):
        """ Handle incoming request. Authenticate. And send downstream. """

        # Prep headers to forward request to wsgi app or remote downstream
        proxy_headers = env.copy()
        for header in proxy_headers.iterkeys():
            # FIXME(ja): this seems bad
            if header.startswith('HTTP_'):
                proxy_headers[header[5:]] = proxy_headers[header]
                del proxy_headers[header]

        # Grab the token from the request
        user_token = self._get_user_token(env)

        # validate the provided token
        token_info = self._validate_user_token(user_token)

        # extract data from the token
        if token_info:
            user_data = self._extract_user_data(token_info)

        # abort if we weren't about to validate the token
        if not (user_token and token_info):
            if self.delay_auth_decision:
                # Allow downstream service to make final decision.
                # Mark status as Invalid and forward the request downstream
                self._decorate_request('X_IDENTITY_STATUS',
                                       'Invalid',
                                       env,
                                       proxy_headers)
                return self._forward_request(env,
                                             start_response,
                                             proxy_headers)
            # Respond to client as appropriate for this auth protocol
            return self._reject_request(env, start_response)

        # Decorate the request with user information
        self._decorate_request('X_IDENTITY_STATUS',
                               'Confirmed',
                               env,
                               proxy_headers)

        # FIXME(ja): what is this?
        self._decorate_request('X_AUTHORIZATION',
                               'Proxy %s' % user_data['user'],
                               env,
                               proxy_headers)

        # For legacy compatibility before we had ID and Name
        self._decorate_request('X_TENANT',
                               user_data['tenant'],
                               env,
                               proxy_headers)

        # Services should use these
        self._decorate_request('X_TENANT_NAME',
                               user_data.get('tenantName',
                                             user_data['tenant']),
                               env,
                               proxy_headers)
        self._decorate_request('X_TENANT_ID',
                               user_data['tenant'],
                               env,
                               proxy_headers)

        self._decorate_request('X_USER',
                               user_data['userName'],
                               env,
                               proxy_headers)
        self._decorate_request('X_USER_ID',
                               user_data['user'],
                               env,
                               proxy_headers)

        # NOTE(lzyeval): claims has a key 'roles' which is
        #                guaranteed to be a list (see note below)
        roles = ','.join(filter(lambda x: x, user_data['roles']))
        self._decorate_request('X_ROLE',
                               roles,
                               env,
                               proxy_headers)

        #Send request downstream
        return self._forward_request(env, start_response, proxy_headers)

    def _get_user_token(self, env):
        """Get token id from request"""
        return env.get('HTTP_X_AUTH_TOKEN', env.get('HTTP_X_STORAGE_TOKEN'))

    def _reject_request(self, env, start_response):
        """Redirect client to auth server"""
        headers = [('WWW-Authenticate',
                    "Keystone uri='%s'" % self.auth_location)]
        resp = webob.exc.HTTPUnauthorized('Authentication required', headers)
        return resp(env, start_response)

    def _reject_token(self, env, start_response):
        """Client sent bad token"""
        resp = webob.exc.HTTPUnauthorized()
        return resp(env, start_response)

    def _ensure_admin_token(self):
        """
        This function gets an admin auth token to be used by this service to
        validate a user's token. Validate_token is a priviledged call so
        it needs to be authenticated by a service that is calling it
        """

        # FIXME(ja): there is more ways to fail/throw exceptions than
        #            KeyError.  We should be VERY verbose with why this
        #            is failing because this function is fundamental breakage
        #            of component configuration.

        if self.admin_token:
            return

        headers = {
            "Content-type": "application/json",
            "Accept": "application/json",
        }
        params = {
            'auth': {
                'passwordCredentials': {
                    'username': self.admin_user,
                    'password': self.admin_password,
                },
                'tenantName': self.admin_tenant_name,
            }
        }
        if self.auth_protocol == "http":
            conn = httplib.HTTPConnection(self.auth_host, self.auth_port)
        else:
            conn = httplib.HTTPSConnection(self.auth_host,
                                           self.auth_port,
                                           cert_file=self.cert_file)
        conn.request("POST",
                     '/v2.0/tokens',
                     json.dumps(params),
                     headers=headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        try:
            self.admin_token = json.loads(data)['access']['token']['id']
        except KeyError:
            return

    def _validate_user_token(self, user_token, retry=True):
        """Validate token, and provide identity information if applicable."""

        if not user_token:
            return

        # Step 1: We need to auth with the keystone service, so get an
        # admin token
        self._ensure_admin_token()

        # FIXME(ja): bug 942984: returning causes the codepath to return
        # unauthorized.  We have a worse situation here - we are unable to
        # retrieve an admin token!  We should error log the fact and the
        # user needs sent 503 (service unavailable) - not 401 unauthorized
        if not self.admin_token:
            return

        # Step 2: validate the user's token with the auth service
        # since this is a priviledged operation, we need to provide
        # an admin token
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'X-Auth-Token': self.admin_token,
        }

        conn = http_connect(self.auth_host,
                            self.auth_port,
                            'GET',
                            '/v2.0/tokens/%s' % user_token,
                            headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()

        # if token is valid return the response text
        if 200 <= resp.status < 300:
            return data
        # if token is unauthorized return
        # FIXME(ja): I'm assuming the 401 status means that user_token is
        #            invalid - not that the admin_token is invalid
        if resp.status == 401:
            return False
        # retry if applicable
        if retry:
            # FIXME(ja): we should only get a new admin_token if the service
            #            tells us that our token is expired.
            self.admin_token = None
            return self._validate_user_token(user_token, False)

    def _extract_user_data(self, data):
        token_info = json.loads(data)
        user = token_info['access']['user']
        token = token_info['access']['token']

        info = {
            'user': user['id'],
            'userName': user['username'],
            'tenant': None,
            'roles': [],
        }

        info['roles'] = [r['name'] for r in user.get('roles', [])]

        # FIXME(ja): comment on why we are checking both places! (is
        # one an older way of doing it?)
        try:
            info['tenant'] = token['tenant']['id']
            info['tenantName'] = token['tenant']['name']
        except:
            info['tenant'] = user.get('tenantId')
            info['tenantName'] = user.get('tenantName')
        # FIXME(ja): if no tenant, legacy auth_token set tenant to None and
        #            had no tenantName. I'm replicating the same for now
        if info['tenantName'] is None:
            del info['tenantName']
        return info

    def _decorate_request(self, index, value, env, proxy_headers):
        """Add headers to request"""
        proxy_headers[index] = value
        env['HTTP_%s' % index] = value

    def _forward_request(self, env, start_response, proxy_headers):
        """Token/Auth processed & claims added to headers"""
        self._decorate_request('AUTHORIZATION',
            'Basic %s' % self.service_pass, env, proxy_headers)
        #now decide how to pass on the call
        if self.app:
            # Pass to downstream WSGI component
            return self.app(env, start_response)
            #.custom_start_response)
        else:
            # We are forwarding to a remote service (no downstream WSGI app)
            req = webob.Request(proxy_headers)
            parsed = urlparse(req.url)

            conn = http_connect(self.service_host,
                                self.service_port,
                                req.method,
                                parsed.path,
                                proxy_headers,
                                ssl=(self.service_protocol == 'https'))
            resp = conn.getresponse()
            data = resp.read()

            #TODO(ziad): use a more sophisticated proxy
            # we are rewriting the headers now

            if resp.status == 401 or resp.status == 305:
                # Add our own headers to the list
                headers = [('WWW_AUTHENTICATE',
                            "Keystone uri='%s'" % self.auth_location)]
                return webob.Response(status=resp.status,
                                      body=data,
                                      headerlist=headers)(env, start_response)
            else:
                return webob.Response(status=resp.status,
                                      body=data)(env, start_response)


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

if __name__ == '__main__':
    app_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            os.pardir,
                            os.pardir,
                            'examples/paste/auth_token.ini')
    app = deploy.loadapp('config:%s' % app_path,
                         global_conf={'log_name': 'auth_token.log'})
    wsgi.server(eventlet.listen(('', 8090)), app)
