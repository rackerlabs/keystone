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
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log
from keystone.openstack.common import timeutils
from keystone import token


CONF = config.CONF
LOG = log.getLogger(__name__)


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
        self.swift.put_object(
            self.token_container,
            token_id,
            jsonutils.dumps(data),
            headers={
                'X-Delete-At': calendar.timegm(data['expires'].timetuple()),
            })

    def delete_token(self, token_id):
        try:
            self.swift.delete_object(self.token_container, token_id)
        except swexc.ClientException:
            LOG.warn('Failed to delete token %s', token_id)

    def delete_tokens(self, user_id, tenant_id=None, trust_id=None,
                      consumer_id=None):
        return super(Token, self).delete_tokens(user_id, tenant_id,
                                                trust_id, consumer_id)

    def _list_tokens(self, user_id, tenant_id=None, trust_id=None,
                     consumer_id=None):
        return super(Token, self)._list_tokens(user_id, tenant_id,
                                               trust_id, consumer_id)

    @staticmethod
    def list_revoked_tokens():
        return ()

    @staticmethod
    def flush_expired_tokens():
        # Nothing to do, handled by Swift expirer.
        pass
