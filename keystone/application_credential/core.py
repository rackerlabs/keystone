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

"""Main entry point into the Application Credential service."""

import uuid

from oslo_log import log

from keystone.common import dependency
from keystone.common import manager
import keystone.conf
from keystone import exception


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


@dependency.requires('identity_api', 'resource_api', 'trust_api')
@dependency.provider('application_credential_api')
class Manager(manager.Manager):
    """Default pivot point for the Application Credential backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.application_credential'

    _APP_CRED = 'application_credential'

    def __init__(self):
        super(Manager, self).__init__(CONF.application_credential.driver)
        # setup notifications

    def _get_application_credential(self, ref):
        ref.pop('trust_id')
        return ref

    def create_application_credential(self, application_credential,
                                      initiator=None):
        """Create a new application credential.

        :returns: a new application credential
        """
        trust = {
            'trustor_user_id': application_credential['user_id'],
            'trustee_user_id': application_credential['user_id'],
            'project_id': application_credential['project_id'],
            'expires_at': application_credential.get('expires_at'),
            'impersonation': False
        }
        trust_id = uuid.uuid4().hex
        roles = application_credential.get('roles') or []
        self.trust_api.create_trust(trust_id, trust, roles,
                                    initiator=initiator)
        application_credential['trust_id'] = trust_id
        ref = self.driver.create_application_credential(
            application_credential)
        return self._get_application_credential(ref)

    def get_application_credential(self, application_credential_id):
        """Get application credential details.

        :returns: an application credential
        """
        ref = self.driver.get_application_credential(
            application_credential_id)
        return self._get_application_credential(ref)

    def list_application_credentials(self, user_id):
        """List application credentials for a user.

        :returns: a plist of application credentials
        """
        refs = self.driver.list_application_credentials_for_user(user_id)
        return [self._get_application_credential(ref) for ref in refs]

    def delete_application_credential(self, application_credential_id,
                                      initiator=None):
        """Delete an application credential.

        :raises keystone.exception.ApplicationCredentialNotFound: If the
            application credential doesn't exist.
        """
        application_credential = self.driver.get_application_credential(
            application_credential_id)
        try:
            self.trust_api.delete_trust(application_credential['trust_id'])
        except exception.TrustNotFound:
            pass
        self.driver.delete_application_credential(application_credential_id)

    def delete_application_credentials_for_user(self, user_id):
        """Delete all application credentials for a user.

        This is triggered when a user is deleted.

        :raises keystone.exception.UserNotFound: If the user is not found.
        """
        # raise UserNotFound if invalid
        self.identity_api.get_user(user_id)
        application_credentials = \
            self.driver.list_application_credentials_for_user(user_id)
        for app_cred in application_credentials:
            self.trust_api.delete_trust(app_cred['trust_id'])
        self.driver.delete_application_credentials_for_user(user_id)

    def delete_application_credentials_for_user_on_project(self, user_id,
                                                           project_id):
        """Delete all application credentials for a user on a given project.

        This is triggered when a user loses a role assignment on a project.

        :raises keystone.exception.UserNotFound: If the user is not found.
        :raises keystone.exception.ProjectNotFound: If the project is not
            found.
        """
        # raise UserNotFound if invalid
        self.identity_api.get_user(user_id)
        # raise ProjectNotFound if invalid
        self.resouce_api.get_project(project_id)
        application_credentials = \
            self.driver.list_application_credentials_for_user(user_id)
        for app_cred in application_credentials:
            if app_cred['project_id'] == project_id:
                self.trust_api.delete_trust(app_cred['trust_id'])
        self.driver.delete_application_credentials_for_user_on_project(
            user_id, project_id)
