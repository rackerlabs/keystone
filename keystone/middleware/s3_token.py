# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011,2012 Akira YOSHIYAMA <akirayoshiyama@gmail.com>
# All Rights Reserved.
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

# This source code is based ./auth_token.py and ./ec2_token.py.
# See them for their copyright.

"""
S3 TOKEN MIDDLEWARE

This WSGI component:

* Get a request from the swift3 middleware with an S3 Authorization
  access key.
* Validate s3 token in Keystone.
* Transform the account name to AUTH_%(tenant_name).

"""

import httplib
import urlparse

import webob

from keystone.openstack.common import jsonutils
from swift.common import utils as swift_utils

PROTOCOL_NAME = 'S3 Token Authentication'


class ServiceError(Exception):
    pass


class S3Token(object):
    """Auth Middleware that handles S3 authenticating client calls."""

    def __init__(self, app, conf):
        """Common initialization code."""
        self.app = app
        self.logger = swift_utils.get_logger(conf, log_route='s3token')
        self.logger.debug('Starting s3token middleware')
        self.reseller_prefix = conf.get('reseller_prefix', 'AUTH_')
        # where to find the auth service (we use this to validate tokens)
        self.s3_url = conf.get('keystone_s3_url',
                               'http://localhost:35357/v2.0/s3tokens')

        # SSL Configuration
        self.cert_file = conf.get('certfile')
        self.key_file = conf.get('keyfile')

        # Legacy configuration
        auth_host = conf.get('auth_host')
        auth_port = conf.get('auth_port')
        auth_protocol = conf.get('auth_protocol')
        if all([auth_host, auth_port, auth_protocol]):
            self.s3_url = '%s://%s:%s/v2.0/s3tokens' % (
                auth_protocol, auth_host, auth_port)

        # This is mostly for the unittest to be overriden.
        self.http_client_class = None

    def deny_request(self, code):
        error_table = {
            'AccessDenied': (401, 'Access denied'),
            'InvalidURI': (400, 'Could not parse the specified URI'),
        }
        resp = webob.Response(content_type='text/xml')
        resp.status = error_table[code][0]
        resp.body = error_table[code][1]
        resp.body = ('<?xml version="1.0" encoding="UTF-8"?>\r\n'
                     '<Error>\r\n  <Code>%s</Code>\r\n  '
                     '<Message>%s</Message>\r\n</Error>\r\n' %
                     (code, error_table[code][1]))
        return resp

    def get_http_client_class(self, scheme):
        if scheme == 'http':
            return httplib.HTTPConnection
        else:
            return httplib.HTTPSConnection

    def _json_request(self, creds_json):
        headers = {'Content-Type': 'application/json'}
        try:
            o = urlparse.urlparse(self.s3_url)

            # We do this to allow the unittest to override
            # http_client_class with its own connection.
            if not self.http_client_class:
                self.http_client_class = self.get_http_client_class(o.scheme)

            if o.scheme == 'http':
                conn = self.http_client_class(o.netloc)
            else:
                conn = self.http_client_class(o.netloc, key_file=self.key_file,
                                              cert_file=self.cert_file)
            conn.request('POST', o.path, body=creds_json, headers=headers)
            response = conn.getresponse()
            output = response.read()
        except Exception as e:
            self.logger.info('HTTP connection exception: %s' % e)
            resp = self.deny_request('InvalidURI')
            raise ServiceError(resp)
        finally:
            conn.close()

        if response.status < 200 or response.status >= 300:
            self.logger.debug('Keystone reply error: status=%s reason=%s' %
                              (response.status, response.reason))
            resp = self.deny_request('AccessDenied')
            raise ServiceError(resp)

        return (response, output)

    def __call__(self, environ, start_response):
        """Handle incoming request. authenticate and send downstream."""
        req = webob.Request(environ)
        self.logger.debug('Calling S3Token middleware.')

        try:
            parts = swift_utils.split_path(req.path, 1, 4, True)
            version, account, container, obj = parts
        except ValueError:
            msg = 'Not a path query, skipping.'
            self.logger.debug(msg)
            return self.app(environ, start_response)

        # Read request signature and access id.
        if 'Authorization' not in req.headers:
            msg = 'No Authorization header. skipping.'
            self.logger.debug(msg)
            return self.app(environ, start_response)

        token = req.headers.get('X-Auth-Token',
                                req.headers.get('X-Storage-Token'))
        if not token:
            msg = 'You did not specify a auth or a storage token. skipping.'
            self.logger.debug(msg)
            return self.app(environ, start_response)

        auth_header = req.headers['Authorization']
        try:
            access, signature = auth_header.split(' ')[-1].rsplit(':', 1)
        except ValueError:
            msg = 'You have an invalid Authorization header: %s'
            self.logger.debug(msg % (auth_header))
            return self.deny_request('InvalidURI')(environ, start_response)

        # NOTE(chmou): This is to handle the special case with nova
        # when we have the option s3_affix_tenant. We will force it to
        # connect to another account than the one
        # authenticated. Before people start getting worried about
        # security, I should point that we are connecting with
        # username/token specified by the user but instead of
        # connecting to its own account we will force it to go to an
        # another account. In a normal scenario if that user don't
        # have the reseller right it will just fail but since the
        # reseller account can connect to every account it is allowed
        # by the swift_auth middleware.
        force_tenant = None
        if ':' in access:
            access, force_tenant = access.split(':')

        # Make a copy of args for authentication and signature verification.
        creds = {
            'credentials': {
                'access': access,
                'signature': signature,
                'token': token,
            }
        }
        creds_json = jsonutils.dumps(creds)
        self.logger.debug('Connecting to Keystone sending this JSON: %s' %
                          creds_json)
        # NOTE(vish): We could save a call to keystone by having
        #             keystone return token, tenant, user, and roles
        #             from this call.
        #
        # NOTE(chmou): We still have the same problem we would need to
        #              change token_auth to detect if we already
        #              identified and not doing a second query and just
        #              pass it through to swiftauth in this case.
        try:
            resp, output = self._json_request(creds_json)
        except ServiceError as e:
            resp = e.args[0]
            msg = 'Received error, exiting middleware with error: %s'
            self.logger.debug(msg % (resp.status))
            return resp(environ, start_response)

        self.logger.debug('Keystone Reply: Status: %d, Output: %s' % (
                          resp.status, output))

        try:
            identity_info = jsonutils.loads(output)
            token_id = str(identity_info['access']['token']['id'])
            tenant = identity_info['access']['token']['tenant']
        except (ValueError, KeyError):
            error = 'Error on keystone reply: %d %s'
            self.logger.debug(error % (resp.status, str(output)))
            return self.deny_request('InvalidURI')(environ, start_response)

        req.headers['X-Auth-Token'] = token_id
        tenant_to_connect = force_tenant or tenant['id']
        self.logger.debug('Connecting with tenant: %s' % (tenant_to_connect))

        new_tenant_name = '%s%s' % (self.reseller_prefix, tenant_to_connect)
        environ['PATH_INFO'] = environ['PATH_INFO'].replace(account,
                                                            new_tenant_name)
        return self.app(environ, start_response)


def filter_factory(global_conf, **local_conf):
    """Returns the WSGI filter for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)
    return lambda app: S3Token(app, conf)
