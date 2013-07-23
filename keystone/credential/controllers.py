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


class CredentialV3(controller.V3Controller):
    collection_name = 'credentials'
    member_name = 'credential'

    def _check_target(self, context, protection, credential_id):
        try:
            ref = self.credential_api.get_credential(credential_id)
        except Exception as e:
            raise e.obfuscate_error()
        self.targetprotected(context, protection, {self.member_name: ref})
        return ref

    @controller.protected
    def create_credential(self, context, credential):
        ref = self._assign_unique_id(self._normalize_dict(credential))
        ref = self.credential_api.create_credential(ref['id'], ref)
        return CredentialV3.wrap_member(context, ref)

    @controller.protected
    def list_credentials(self, context):
        refs = self.credential_api.list_credentials()
        return CredentialV3.wrap_collection(context, refs)

    @controller.prepareprotection
    def get_credential(self, context, protection, credential_id):
        ref = self._check_target(context, protection, credential_id)
        return CredentialV3.wrap_member(context, ref)

    @controller.prepareprotection
    def update_credential(self, context, protection,
                          credential_id, credential):
        self._check_target(context, protection, credential_id)
        self._require_matching_id(credential_id, credential)

        ref = self.credential_api.update_credential(credential_id, credential)
        return CredentialV3.wrap_member(context, ref)

    @controller.prepareprotection
    def delete_credential(self, context, protection, credential_id):
        self._check_target(context, protection, credential_id)
        return self.credential_api.delete_credential(credential_id)
