# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Red Hat, Inc
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

import copy
import uuid

from keystone import exception
from keystone.common import logging
from keystone.common import wsgi
from keystone.identity import Manager as IdentityManager
from keystone.token import Manager as TokenManager


LOG = logging.getLogger(__name__)


class UserController(wsgi.Application):
    def __init__(self):
        self.identity_api = IdentityManager()
        self.token_api = TokenManager()

    def set_user_password(self, context, user_id, user):
        token_id = context.get('token_id')
        original_password = user.get('original_password')

        token_ref = self.token_api.get_token(context=context,
                                            token_id=token_id)
        user_id_from_token = token_ref['user']['id']

        if user_id_from_token != user_id or original_password is None:
            raise exception.Forbidden()

        try:
            self.identity_api.authenticate(context=context,
                                           user_id=user_id_from_token,
                                           password=original_password)
        except AssertionError:
            raise exception.Unauthorized()

        update_dict = {'password': user['password'], 'id': user_id}

        self.identity_api.update_user(context, user_id, update_dict)
        try:
            for token_id in self.token_api.list_tokens(context, user_id):
                self.token_api.delete_token(context, token_id)
        except exception.NotImplemented:
            # The password has been changed but tokens remain valid for
            # backends that can't list tokens for users
            LOG.warning('Password changed for %s, but existing tokens remain '
                        'valid' % user_id)

        token_id = uuid.uuid4().hex
        new_token_ref = copy.copy(token_ref)
        new_token_ref["id"] = token_id
        self.token_api.create_token(context=context, token_id=token_id,
                                    data=new_token_ref)
        logging.debug('TOKEN_REF %s', token_ref)
        return {'access': {'token': new_token_ref}}


class CrudExtension(wsgi.ExtensionRouter):
    """

    Provides a subset of CRUD operations for internal data types.

    """

    def add_routes(self, mapper):
        user_controller = UserController()

        mapper.connect('/users/{user_id}/OS-KSCRUD/password',
                       controller=user_controller,
                       action='set_user_password',
                       conditions=dict(method=['PUT']))
