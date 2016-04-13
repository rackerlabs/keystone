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

from keystone.identity.backends import shadow
from keystone.identity.shadow_backends import base


class ShadowUsers(base.ShadowUsersDriverV9):
    def create_federated_user(self, federated_dict):
        return shadow.ShadowUsers().create_federated_user(federated_dict)

    def get_federated_user(self, idp_id, protocol_id, unique_id):
        return shadow.ShadowUsers().get_federated_user(idp_id, protocol_id,
                                                       unique_id)

    def update_federated_user_display_name(self, idp_id, protocol_id,
                                           unique_id, display_name):
        return shadow.ShadowUsers().update_federated_user_display_name(
            idp_id, protocol_id, unique_id, display_name)
