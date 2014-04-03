# -*- coding: utf-8 -*-

# Copyright 2014 eNovance
# Author: Julien Danjou <julien@danjou.info>
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

import calendar

from swiftclient import client as swclient
from swiftclient import exceptions as swexc

from keystone import config
from keystone import exception
from keystone import token
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils

CONF = config.CONF


class Token(token.Driver):
    """Swift backend for tokens."""

    def __init__(self):
        self.swift = swclient.Connection(
            auth_version=CONF.swift.swift_auth_version,
            authurl=CONF.swift.swift_authurl,
            preauthurl=CONF.swift.swift_preauthurl,
            preauthtoken=CONF.swift.swift_preauthtoken,
            user=CONF.swift.swift_user,
            key=CONF.swift.swift_key,
            tenant_name=CONF.swift.swift_tenant_name)
        self.token_container = CONF.swift.swift_token_container
        self.swift.put_container(self.token_container)

    def get_token(self, token_id):
        try:
            headers, obj = self.swift.get_object(
                self.token_container, token_id)
        except swexc.ClientException:
            raise exception.TokenNotFound(token_id=token_id)
        token = jsonutils.loads(obj)
        token['expires'] = timeutils.parse_isotime(token['expires'])
        return token

    def create_token(self, token_id, data):
        headers = {'X-Delete-At':
                   calendar.timegm(data['expires'].timetuple())}
        self.swift.put_object(self.token_container,
                              token_id,
                              jsonutils.dumps(data),
                              headers=headers)
        self.swift.put_container('tokens_for_user_'
                                 + data['user']['id'])
        self.swift.put_object('tokens_for_user_'
                              + data['user']['id'], token_id,
                              "",
                              headers=headers)
        self.swift.put_container('tokens_for_tenant_'
                                 + data['tenant']['id'])
        self.swift.put_object('tokens_for_tenant_'
                              + data['tenant']['id'], token_id,
                              "",
                              headers=headers)
        if 'trust_id' in data:
            self.swift.put_container('tokens_for_trust_'
                                     + data['trust_id'])
            self.swift.put_object('tokens_for_trust_'
                                  + data['trust_id'], token_id,
                                  "",
                                  headers=headers)

    def delete_token(self, token_id):
        headers, obj = self.swift.get_object(self.token_container, token_id)
        try:
            self.swift.delete_object(self.token_container, token_id)
        except swexc.ClientException:
            LOG.warn("Failed to delete token %s in per user container %s",
                     token_id, obj['user']['id'])
        token = jsonutils.loads(obj)
        try:
            self.swift.delete_object('tokens_for_user_'
                                     + obj['user']['id'], token_id)
        except swexc.ClientException:
            # It's not so bad if can't delete it, just log it
            LOG.warn("Unable to delete token %s in per user container %s",
                     token_id, obj['user']['id'])
        try:
            self.swift.delete_object('tokens_for_tenant_'
                                     + obj['tenant']['id'], token_id)
        except swexc.ClientException:
            # It's not so bad if can't delete it, just log it
            LOG.warn("Unable to delete token %s in per tenant container %s",
                     token_id, obj['tenant']['id'])
        if 'trust_id' in token:
            try:
                self.swift.delete_object('tokens_for_trust_'
                                         + obj['trust_id'], token_id)
            except swexc.ClientException:
                # It's not so bad if can't delete it, just log it
                LOG.warn("Unable to delete token %s in per trust container %s",
                         token_id, obj['trust_id'])

    def delete_tokens(self, user_id, tenant_id=None, trust_id=None,
                      consumer_id=None):
        return super(Token, self).delete_tokens(user_id, tenant_id, trust_id, consumer_id)

    def _list_tokens(self, user_id, tenant_id=None, trust_id=None,
                     consumer_id=None):
        headers, user_tokens_obj = self.swift.get_containers(user_id)
        tokens_for_user = set(obj['name'] for obj in user_tokens_obj)

        if tenant_id is not None:
            headers, tenant_tokens_obj = self.swift.get_containers(user_id)
        else:
            tenant_tokens_obj = ()
        tokens_for_tenant = set(obj['name'] for obj in tenant_tokens_obj)

        if trust_id is not None:
            headers, trust_tokens_obj = self.swift.get_containers(user_id)
        else:
            trust_tokens_obj = ()
        tokens_for_trust = set(obj['name'] for obj in trust_tokens_obj)

        if consumer_id is not None:
            headers, consumer_tokens_obj = self.swift.get_containers(user_id)
        else:
            consumer_tokens_obj = ()
        tokens_for_consumer = set(obj['name'] for obj in consumer_tokens_obj)

        return tokens_for_user.intersect(tokens_for_tenant,
                                         tokens_for_trust,
                                         tokens_for_consumer)

    def list_revoked_tokens(self):
        return ()

    def flush_expired_tokens(self):
        # Nothing to do, handled by Swift expirer.
        pass
