# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""
Starting point for routing EC2 requests.

"""

import socket
import urlparse

from eventlet.green import httplib
from keystoneclient.openstack.common import jsonutils
from keystoneclient.openstack.common import memorycache
from nova import wsgi
from oslo.config import cfg
import webob.dec
import webob.exc


ec2_opts = [
    cfg.IntOpt('keystone_ec2_cache_exipration',
               default=15,
               help='Time in seconds for cache expiration.')
]
CONF = cfg.CONF
CONF.register_opts(ec2_opts)


class EC2Token(wsgi.Middleware):
    """Authenticate an EC2 request with keystone and convert to token."""
    def __init__(self, app, conf):
        self._cache_initialized = False    # cache already initialzied?
        self.http_client_class = None  # This is to help with the unittests
        super(EC2Token, self).__init__(app)

    def _init_cache(self):
        self._cache = memorycache.get_client()
        self._cache_initialized = True

    def _return_results(self, req, result):
        try:
            token_id = result['access']['token']['id']
        except (TypeError, AttributeError, KeyError):
            raise webob.exc.HTTPBadRequest()

        # Authenticated!
        req.headers['X-Auth-Token'] = token_id
        return self.application

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        if not self._cache_initialized:
            self._init_cache()

        # Read request signature and access id.
        try:
            signature = req.params['Signature']
            access = req.params['AWSAccessKeyId']
        except KeyError:
            raise webob.exc.HTTPBadRequest()

        cache_key = 'ec2Signature-%s' % (signature)

        data = self._cache.get(cache_key)
        if data:
            return self._return_results(req, data)

        # Make a copy of args for authentication and signature verification.
        auth_params = dict(req.params)
        # Not part of authentication args
        auth_params.pop('Signature')

        # Authenticate the request.
        creds = {
            'ec2Credentials': {
                'access': access,
                'signature': signature,
                'host': req.host,
                'verb': req.method,
                'path': req.path,
                'params': auth_params,
            }
        }
        creds_json = jsonutils.dumps(creds)
        headers = {'Content-Type': 'application/json'}

        o = urlparse.urlparse(CONF.keystone_ec2_url)
        if self.http_client_class:
            conn = self.http_client_class(o.netloc)
        elif o.scheme == 'http':
            conn = httplib.HTTPConnection(o.netloc)
        else:
            conn = httplib.HTTPSConnection(o.netloc)
        try:
            conn.request('POST', o.path, body=creds_json, headers=headers)
            response = conn.getresponse().read()
        except socket.error:
            # TODO(chmou): Logging
            raise webob.exc.HTTPBadRequest()
        else:
            conn.close()

        resp = self._return_results(req, jsonutils.loads(response))
        self._cache.set(cache_key, data, CONF.keystone_ec2_cache_exipration)
        return resp
