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

import os

import keystone.conf
from keystone.token.providers import base

CONF = keystone.conf.CONF


class Provider(base.Provider):

    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

        # NOTE(lbragstad): We add these checks here because if the jwt
        # provider is going to be used and either the `key_repository` is empty
        # or doesn't exist we should fail, hard. It doesn't make sense to start
        # keystone and just 500 because we can't do anything with an empty or
        # non-existant key repository.
        if not os.path.exists(CONF.jwt_tokens.key_repository):
            subs = {'key_repo': CONF.jwt_tokens.key_repository}
            raise SystemExit(_('%(key_repo)s does not exist') % subs)
        if not os.listdir(CONF.jwt_tokens.key_repository):
            subs = {'key_repo': CONF.jwt_tokens.key_repository}
            raise SystemExit(_('%(key_repo)s does not contain keys, use '
                               'keystone-manage jwt_setup to create '
                               'JWT keys.') % subs)

        self.token_formatter = JWTFormatter()

    def generate_id_and_issued_at(self, token):
        pass

    def validate_token(self, token_id):
        pass


class JWTFormatter(object):

    def create_token(self, token):
        pass

    def validate_token(self, token_id):
        pass
