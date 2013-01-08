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


from keystone.common import logging
from keystone import auth
from keystone import exception
from keystone import identity


METHOD_NAME = 'password'

LOG = logging.getLogger(__name__)


class UserAuthInfo(object):
    def __init__(self, auth_info):
        self.user_id = None
        self.password = None
        self.user_ref = None
        self._validate_and_normalize_auth_data(auth_info)

    def _validate_and_normalize_auth_data(self, auth_info):
        user_info = auth_info.get_method_data(METHOD_NAME)
        if 'user' not in user_info:
            raise exception.ValidationError(attribute='user',
                                            target=METHOD_NAME)
        self.user_ref = auth_info.lookup_user(user_info['user'])
        self.user_id = self.user_ref['id']
        self.password = user_info['user'].get('password', None)


class Password(auth.AuthMethodHandler):
    def authenticate(self, context, auth_info, user_context):
        """ Try to authenticate against the identity backend. """
        user_info = UserAuthInfo(auth_info)
        (domain_id, project_id) = auth_info.get_scope()

        # FIXME: identity.authenticate() can use some refactoring since
        # all we care is password matches
        user_auth_data = self.identity_api.authenticate(
            context=context,
            user_id=user_info.user_id,
            password=user_info.password,
            tenant_id=project_id)
        if 'user_id' not in user_context:
            user_context['user_id'] = user_info.user_id
