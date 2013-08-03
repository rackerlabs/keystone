# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

from keystone import auth
from keystone import exception
from keystone import identity

from keystone.auth import auth_utils
from keystone.openstack.common import log as logging


METHOD_NAME = 'password'

LOG = logging.getLogger(__name__)


class UserAuthInfo(object):
    def __init__(self, auth_payload):
        self.auth_utils = auth_utils.AuthUtils()
        self.identity_api = identity.Manager()
        self.user_id = None
        self.password = None
        self.user_ref = None
        self._validate_and_normalize_auth_data(auth_payload)

    def _validate_and_normalize_auth_data(self, auth_payload):
        if 'user' not in auth_payload:
            raise exception.ValidationError(attribute='user',
                                            target=METHOD_NAME)
        user_info = auth_payload['user']
        self.password = user_info.get('password', None)
        user_ref, domain_ref = self.auth_utils.lookup_user(user_info)
        self.user_ref = user_ref
        self.user_id = user_ref['id']
        self.domain_id = domain_ref['id']


class Password(auth.AuthMethodHandler):
    def authenticate(self, context, auth_payload, user_context):
        """Try to authenticate against the identity backend."""
        user_info = UserAuthInfo(auth_payload)

        # FIXME(gyee): identity.authenticate() can use some refactoring since
        # all we care is password matches
        try:
            self.identity_api.authenticate(
                user_id=user_info.user_id,
                password=user_info.password,
                domain_scope=user_info.domain_id)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = _('Invalid username or password')
            raise exception.Unauthorized(msg)

        if 'user_id' not in user_context:
            user_context['user_id'] = user_info.user_id
