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


from keystone import exception
from keystone import auth
from keystone import identity
from keystone.common import dependency
from keystone.common import logging


METHOD_NAME = 'password'

LOG = logging.getLogger(__name__)


# (gyee) dependency injection doesn't seem to work with importutils
# do the explicit import for now.
#@dependency.requires('identity_api')
class UserAuthInfo(object):
    def __init__(self, context, auth_info):
        self.identity_api = identity.Manager()
        self.context = context
        self.auth_info = auth_info
        self._payload = auth_info.get_method_data(METHOD_NAME)
        self.user_id = None
        self.password = None
        self.user_ref = None
        self._validate_and_normalize_auth_data()

    def _validate_and_normalize_auth_data(self):
        if 'user' not in self._payload:
            raise exception.ValidationError(attribute='user',
                                            target=METHOD_NAME)

        user_id = self._payload['user'].get('id', None)
        username = self._payload['user'].get('name', None)
        self.password = self._payload['user'].get('password', None)
        if user_id is None and username is None:
            raise exception.ValidationError(attribute='id or name',
                                            target='user')
        # make sure user exist
        try:
            if username:
                self.user_ref = self.identity_api.get_user_by_name(
                    context=self.context, user_name=username)
            else:
                self.user_ref = self.identity_api.get_user(
                    context=self.context, user_id=user_id)
        except exception.UserNotFound as e:
            raise exception.Unauthorized(e)
        print 'user_ref=%s' % self.user_ref
        self.user_id = self.user_ref['id']

        # TODO(gyee): do we care if password is None?
        self.password = self._payload['user'].get('password', None)


class Password(auth.AuthMethodHandler):
    def authenticate(self, context, auth_info, user_context):
        """ Try to authenticate against the identity backend. """
        user_info = UserAuthInfo(context, auth_info)
        (domain_id, project_id) = auth_info.get_scope()

        try:
            # identity.authenticate() can use some refactoring since
            # all we care is password matches
            user_auth_data = self.identity_api.authenticate(
                context=context,
                user_id=user_info.user_id,
                password=user_info.password,
                tenant_id=project_id)
            if 'user_id' not in user_context:
                user_context['user_id'] = user_info.user_id
        except AssertionError as e:
            LOG.error(e)
            raise exception.Unauthorized(e)
