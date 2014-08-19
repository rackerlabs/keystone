# Copyright 2013 Metacloud, Inc.
# Copyright 2012 OpenStack Foundation
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

from keystone.common import config
from keystone.token.persistence import core


CONF = config.CONF


class Token(core.Driver):
    """A token driver that is meant to be used with non-persistent provider.

    This driver simply raises NotImplementedError() in all cases to allow for
    validation that the token_api is not being called unexpectedly. This driver
    should be used if tokens should not be persisted.
    """

    def create_token(self, token_id, data):
        raise NotImplementedError()

    def get_token(self, token_id):
        raise NotImplementedError()

    def delete_token(self, token_id):
        raise NotImplementedError()

    def _list_tokens(self, user_id, tenant_id=None, trust_id=None,
                     consumer_id=None):
        raise NotImplementedError()

    def delete_tokens(self, user_id, tenant_id=None, trust_id=None,
                      consumer_id=None):
        raise NotImplementedError()

    def list_revoked_tokens(self):
        raise NotImplementedError()

    def flush_expired_tokens(self):
        raise NotImplementedError()
