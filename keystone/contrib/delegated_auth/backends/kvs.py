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

import uuid

from keystone.common import kvs
from keystone.openstack.common import timeutils


class DelegatedAuth(kvs.Base):
    def get_consumer(self, consumer_id):
        return self.db.get('consumer-%s' % consumer_id)

    def create_consumer(self, consumer):
        consumer_id = consumer['id']
        consumer['consumer_key'] = consumer_id
        consumer['consumer_secret'] = uuid.uuid4().hex
        self.db.set('consumer-%s' % consumer_id, consumer)
        consumer_list = set(self.db.get('consumer_list', []))
        consumer_list.add(consumer_id)
        self.db.set('consumer_list', list(consumer_list))
        return consumer

    def delete_consumer(self, consumer_id):
        # call get to make sure it exists
        self.db.get('consumer-%s' % consumer_id)
        self.db.delete('consumer-%s' % consumer_id)
        consumer_list = set(self.db.get('consumer_list', []))
        consumer_list.remove(consumer_id)
        self.db.set('consumer_list', list(consumer_list))

    def list_consumers(self):
        consumer_ids = self.db.get('consumer_list', [])
        return [self.get_consumer(x) for x in consumer_ids]

    def update_consumer(self, consumer_id, consumer):
        # call get to make sure it exists
        self.db.get('consumer-%s' % consumer_id)
        self.db.set('consumer-%s' % consumer_id, consumer)
        return consumer

    def create_request_token(self, consumer_key, roles, request_hash,
                             verifier):
        request_token = {}
        request_token_id = uuid.uuid4().hex
        request_token['key'] = request_token_id
        request_token['id'] = request_token_id
        request_token['key_hash'] = request_hash
        request_token['secret'] = uuid.uuid4().hex
        request_token['verifier'] = verifier
        request_token['user_id'] = None
        request_token['tenant_id'] = None
        request_token['requested_roles'] = roles
        request_token['consumer_key'] = consumer_key
        request_token['issued_at'] = timeutils.isotime(subsecond=True)
        self.db.set('request_token-%s' % request_token_id, request_token)
        return request_token

    def get_request_token(self, request_token_id):
        return self.db.get('request_token-%s' % request_token_id)

    def authorize_request_token(self, request_token_id, user_id, tenant_id):
        request_token = self.db.get('request_token-%s' % request_token_id)
        request_token['user_id'] = user_id
        request_token['tenant_id'] = tenant_id
        self.db.set('request_token-%s' % request_token_id, request_token)
        return request_token

    def create_access_token(self, user_id, tenant_id, consumer_key, roles):
        access_token = {}
        access_token_id = uuid.uuid4().hex
        access_token['id'] = access_token_id
        access_token['key'] = access_token_id
        access_token['secret'] = uuid.uuid4().hex
        access_token['user_id'] = user_id
        access_token['tenant_id'] = tenant_id
        access_token['requested_roles'] = roles
        access_token['consumer_key'] = consumer_key
        access_token['issued_at'] = timeutils.isotime(subsecond=True)
        self.db.set('access_token-%s' % access_token_id, access_token)
        #update user list too
        user_auth_list = set(self.db.get('auth_list-%s' % user_id, []))
        user_auth_list.add(access_token_id)
        self.db.set('auth_list-%s' % user_id, list(user_auth_list))
        return access_token

    def get_access_token(self, access_token_id):
        return self.db.get('access_token-%s' % access_token_id)

    def list_user_authorizations(self, user_id):
        user_auth_list = self.db.get('auth_list-%s' % user_id, [])
        return [self.get_access_token(x) for x in user_auth_list]

    def delete_user_authorization(self, user_id, access_token_id):
        access_token = self.get_access_token(access_token_id)
        access_token['user_id'] = None
        access_token['tenant_id'] = None
        self.db.set('access_token-%s' % access_token_id, access_token)
        #self.db.delete('access_token-%s' % access_token_id)
        user_auth_list = set(self.db.get('auth_list-%s' % user_id, []))
        user_auth_list.remove(access_token_id)
        self.db.set('auth_list-%s' % user_id, list(user_auth_list))
