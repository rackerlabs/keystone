# Copyright 2017 SUSE Linux GmbH
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

"""Workflow Logic the Application Credential service."""

from oslo_log import log

from keystone.common import controller
from keystone.common import dependency
from keystone.common import validation
import keystone.conf
from keystone import exception
from keystone.i18n import _
from keystone.application_credential import schema


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


@dependency.requires('identity_api')
#@dependency.requires('identity_api', 'application_credential_api')
class ApplicationCredentialV3(controller.V3Controller):
    collection_name = 'application_credentials'
    member_name = 'application_credential'

    @controller.protected()
    def create_application_credential(self, request, user_id, application_credential):
        validation.lazy_validate(schema.application_credential_create, application_credential)
        app_cred = self._normalize_dict(application_credential)
        #ref = self.application_credential_api.create_application_credential(
        #    app_cred_id, app_cred, initiator=request.audit_initiator
        #)
        ref = { 'id': 'fake' }
        return ApplicationCredentialV3.wrap_member(request.context_dict, ref)

    @controller.protected()
    def list_application_credentials(self, request,  user_id):
        #refs = self.application_credential_api.list_application_credentials(
        #    user_id, hints=hints)
        refs = [{'id': 'fake' }]
        return ApplicationCredentialV3.wrap_collection(request.context_dict, refs)


    @controller.protected()
    def get_application_credential(self, request, user_id, application_credential_id):
        #ref = self.application_credential_api.get_application_credential(
        #    app_cred_id)
        ref = {'id': 'fake' }
        return ApplicationCredentialV3.wrap_member(request.context_dict, ref)

    @controller.protected()
    def delete_application_credential(self, request, user_id, application_credential_id):
        #return self.application_credential_api.delete_application_credential(
        #    app_cred_id, initiator=request.audit_initiator
        #)
        return None
