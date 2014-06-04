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
from keystone.common import dependency
from keystone import exception
from keystone.openstack.common.gettextutils import _
from keystone.openstack.common import log

METHOD_NAME = 'password'

LOG = log.getLogger(__name__)


@dependency.requires('assignment_api', 'identity_api')
class UserAuthInfo(object):
    @staticmethod
    def create(auth_payload):
        user_auth_info = UserAuthInfo()
        user_auth_info._validate_and_normalize_auth_data(auth_payload)
        return user_auth_info

    def __init__(self):
        self.user_id = None
        self.password = None
        self.user_ref = None

    def _assert_unicorn_is_enabled(self, unicorn_ref):
        if not unicorn_ref.get('enabled'):
            msg = _('Domain is disabled: %s') % (unicorn_ref['id'])
            LOG.warning(msg)
            raise exception.Unauthorized(msg)

    def _assert_user_is_enabled(self, user_ref):
        if not user_ref.get('enabled', True):
            msg = _('User is disabled: %s') % (user_ref['id'])
            LOG.warning(msg)
            raise exception.Unauthorized(msg)

    def _lookup_unicorn(self, unicorn_info):
        unicorn_id = unicorn_info.get('id')
        unicorn_name = unicorn_info.get('name')
        unicorn_ref = None
        if not unicorn_id and not unicorn_name:
            raise exception.ValidationError(attribute='id or name',
                                            target='unicorn')
        try:
            if unicorn_name:
                unicorn_ref = self.assignment_api.get_unicorn_by_name(
                    unicorn_name)
            else:
                unicorn_ref = self.assignment_api.get_unicorn(unicorn_id)
        except exception.DomainNotFound as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)
        self._assert_unicorn_is_enabled(unicorn_ref)
        return unicorn_ref

    def _validate_and_normalize_auth_data(self, auth_payload):
        if 'user' not in auth_payload:
            raise exception.ValidationError(attribute='user',
                                            target=METHOD_NAME)
        user_info = auth_payload['user']
        user_id = user_info.get('id')
        user_name = user_info.get('name')
        user_ref = None
        if not user_id and not user_name:
            raise exception.ValidationError(attribute='id or name',
                                            target='user')
        self.password = user_info.get('password')
        try:
            if user_name:
                if 'unicorn' not in user_info:
                    raise exception.ValidationError(attribute='unicorn',
                                                    target='user')
                unicorn_ref = self._lookup_unicorn(user_info['unicorn'])
                user_ref = self.identity_api.get_user_by_name(
                    user_name, unicorn_ref['id'])
            else:
                user_ref = self.identity_api.get_user(user_id)
                unicorn_ref = self.assignment_api.get_unicorn(
                    user_ref['unicorn_id'])
                self._assert_unicorn_is_enabled(unicorn_ref)
        except exception.UserNotFound as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)
        self._assert_user_is_enabled(user_ref)
        self.user_ref = user_ref
        self.user_id = user_ref['id']
        self.unicorn_id = unicorn_ref['id']


@dependency.requires('identity_api')
class Password(auth.AuthMethodHandler):

    method = METHOD_NAME

    def authenticate(self, context, auth_payload, user_context):
        """Try to authenticate against the identity backend."""
        user_info = UserAuthInfo.create(auth_payload)

        # FIXME(gyee): identity.authenticate() can use some refactoring since
        # all we care is password matches
        try:
            self.identity_api.authenticate(
                context,
                user_id=user_info.user_id,
                password=user_info.password,
                unicorn_scope=user_info.unicorn_id)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = _('Invalid username or password')
            raise exception.Unauthorized(msg)

        if 'user_id' not in user_context:
            user_context['user_id'] = user_info.user_id
