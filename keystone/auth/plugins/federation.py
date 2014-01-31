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
from keystone.common import dependency
from keystone import exception
from keystone.openstack.common import log
from keystone.openstack.common import timeutils


LOG = log.getLogger(__name__)


@dependency.requires('token_api')
class Federation(auth.AuthMethodHandler):

    method = 'federation'

    def _validate_expiration(self, token_ref):
        expires_at = token_ref['expires']
        if expires_at:
            now = timeutils.utcnow()
#            expires = timeutils.normalize_time(
#                timeutils.parse_isotime(expires_at))
            if now > expires_at:
                raise exception.Unauthorized(_('Access token is expired'))
        return expires_at

    def authenticate(self, context, auth_info, auth_context):
        """Turn unscoped federated token to a valid, scoped one."""
        try:
            federated_token_id = auth_info['id']
        except KeyError:
            raise exception.ValidationError(
                attribute='federated_token', target=self.method)
        token_ref = self.token_api.get_token(federated_token_id)
        auth_context['expires_at'] = self._validate_expiration(token_ref)
        auth_context['user_id'] = token_ref['user_id']
        auth_context['federated_token_id'] = federated_token_id
        auth_context['federated_token'] = token_ref
