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

from keystone.application_credential import schema
from keystone.common import controller
from keystone.common import validation
import keystone.conf
from keystone import exception
from keystone.i18n import _


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


class ApplicationCredentialV3(controller.V3Controller):
    collection_name = 'application_credentials'
    member_name = 'application_credential'
    _public_parameters = frozenset([
        'id',
        'name',
        'description',
        'expires_at',
        'project_id',
        'roles',
        # secret is only expose after create, it is not stored
        'secret',
        'allow_application_credential_creation'
    ])

    def _normalize_role_list(self, trust_roles):
        roles = []
        for role in trust_roles:
            if role.get('id'):
                roles.append({'id': role['id']})
            else:
                roles.append(self.role_api.get_role_by_name(role['name']))
        return roles

    def _generate_secret(self):
        # TODO(me) securely generate a random 255-byte string
        return 'hunter2'

    @classmethod
    def wrap_member(cls, context, ref):
        ref = cls.filter_params(ref)
        return super(ApplicationCredentialV3, cls).wrap_member(context,
                                                               ref)

    @classmethod
    def wrap_collection(cls, context, refs, hints=None):
        refs = [cls.filter_params(ref) for ref in refs]
        return super(ApplicationCredentialV3, cls).wrap_collection(context,
                                                                   refs,
                                                                   hints=hints)

    @controller.protected()
    def create_application_credential(self, request, user_id,
                                      application_credential):
        validation.lazy_validate(schema.application_credential_create,
                                 application_credential)
        if request.context.user_id != user_id:
            action = _("Cannot create an application credential for another "
                       "user")
            raise exception.ForbiddenAction(action=action)
        project_id = request.context.project_id
        if not project_id:
            action = _("Must be scoped to a project to create an application "
                       "credential")
            raise exception.ForbiddenAction(action=action)
        app_cred = self._assign_unique_id(application_credential)
        if not app_cred.get('secret'):
            app_cred['secret'] = self._generate_secret()
        app_cred['user_id'] = user_id
        app_cred['project_id'] = project_id
        app_cred['roles'] = self._normalize_role_list(app_cred['roles'])
        app_cred = self._normalize_dict(app_cred)
        ref = self.application_credential_api.create_application_credential(
            app_cred, initiator=request.audit_initiator
        )
        return ApplicationCredentialV3.wrap_member(request.context_dict, ref)

    @controller.protected()
    def list_application_credentials(self, request, user_id):
        refs = self.application_credential_api.list_application_credentials(
            user_id)
        return ApplicationCredentialV3.wrap_collection(request.context_dict,
                                                       refs)

    @controller.protected()
    def get_application_credential(self, request, user_id,
                                   application_credential_id):
        ref = self.application_credential_api.get_application_credential(
            application_credential_id)
        return ApplicationCredentialV3.wrap_member(request.context_dict, ref)

    @controller.protected()
    def delete_application_credential(self, request, user_id,
                                      application_credential_id):
        self.application_credential_api.delete_application_credential(
            application_credential_id, initiator=request.audit_initiator
        )
