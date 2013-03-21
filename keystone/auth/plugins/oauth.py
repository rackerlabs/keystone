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

import datetime

from keystone import auth
from keystone.common import dependency
from keystone.common import logging
from keystone.common import oauth
from keystone.contrib import oauth1
from keystone import exception


METHOD_NAME = 'oauth'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

LOG = logging.getLogger(__name__)


@dependency.requires('oauth_api')
class OAuth(auth.AuthMethodHandler):
    def __init__(self):
        self.oauth_api = oauth1.Manager()

    def authenticate(self, context, auth_payload, auth_context):
        """Turn a signed request with an access key into a keystone token."""
        request = context['request']
        access_token_id = auth_payload.get('access_token_id')

        if not access_token_id:
            raise exception.ValidationError(
                attribute='oauth_token', target='request')

        acc_token = self.oauth_api.get_access_token(access_token_id)
        consumer_id = acc_token['consumer_id']
        consumer = self.oauth_api._get_consumer(consumer_id)

        expires_at = acc_token['expires_at']
        if expires_at:
            now = datetime.datetime.utcnow()
            expires = datetime.datetime.strptime(expires_at, TIME_FORMAT)
            if now > expires:
                raise exception.Unauthorized(_('Access token is expired'))

        consumer_obj = oauth.Consumer(key=consumer['id'],
                                      secret=consumer['consumer_secret'])
        acc_token_obj = oauth.Token(key=acc_token['id'],
                                    secret=acc_token['access_secret'])

        url = oauth1.rebuild_url_from_environ(request.environ)
        oauth_request = oauth.Request.from_request(
            http_method='POST',
            http_url=url,
            headers=request.headers,
            query_string=request.query_string)
        oauth_server = oauth.Server()
        oauth_server.add_signature_method(oauth.SignatureMethod_HMAC_SHA1())
        params = oauth_server.verify_request(oauth_request,
                                             consumer_obj,
                                             token=acc_token_obj)

        if len(params) != 0:
            msg = _('There should not be any non-oauth parameters')
            raise exception.Unauthorized(message=msg)

        auth_context['user_id'] = acc_token['authorizing_user_id']
        auth_context['access_token_id'] = access_token_id
