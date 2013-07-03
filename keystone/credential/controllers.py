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

from keystone.common import controller
from keystone.credential import credential as c


class CredentialV3(controller.V3Controller):
    collection_name = 'credentials'
    member_name = 'credential'

    @controller.protected
    def create_credential(self, context, credential):
        ref = c.Credential.create(**self._normalize_dict(credential))
        return self.wrap_member(context, ref)

    @controller.protected
    def list_credentials(self, context):
        refs = c.Credential.list()
        return self.wrap_collection(context, refs)

    @controller.protected
    def get_credential(self, context, credential_id):
        ref = c.Credential.get(credential_id)
        return self.wrap_member(context, ref)

    @controller.protected
    def update_credential(self, context, credential_id, credential):
        self._require_matching_id(credential_id, credential)
        credential['id'] = credential_id
        ref = c.Credential.update(**credential)
        return self.wrap_member(context, ref)

    @controller.protected
    def delete_credential(self, context, credential_id):
        c.Credential.delete(credential_id)
