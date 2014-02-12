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

from keystone.common import controller
from keystone.common import dependency
from keystone import exception


@dependency.requires('identity_api')
class V3Controller(controller.V3Controller):

#    @controller.protected()
    def rotate_password(self, context, user_id, user):
        """Description of the controller logic."""
        original_password = user.get('original_password')
        if original_password is None:
            raise exception.ValidationError(target='user',
                                            attribute='original_password')

        password = user.get('password')
        if password is None:
            raise exception.ValidationError(target='user',
                                            attribute='password')

        domain_scope = self._get_domain_id_for_request(context)
        try:
            self.identity_api.rotate_password(user_id, original_password,
                                              password, domain_scope)
        except AssertionError:
            raise exception.Unauthorized()

#    @controller.protected()
    def expire_old_passwords(self, context, user_id):
        """Description of the controller logic."""
        self.identity_api.expire_old_passwords(user_id)
