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

from keystone.common import manager
from keystone.common import password_hashing
import keystone.conf
from keystone import exception
from keystone import notifications


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


class Manager(manager.Manager):
    """Default pivot point for the Application Credential backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.application_credential'
    _provides_api = 'application_credential_api'

    _APP_CRED = 'application_credential'

    def __init__(self):
        super(Manager, self).__init__(CONF.application_credential.driver)
        self._register_callback_listeners()

    def _register_callback_listeners(self):
        notifications.register_event_callback(
            notifications.ACTIONS.deleted, 'user',
            self._delete_app_creds_on_user_delete_callback)
        notifications.register_event_callback(
            notifications.ACTIONS.disabled, 'user',
            self._delete_app_creds_on_user_delete_callback)
        notifications.register_event_callback(
            notifications.ACTIONS.deleted, 'role_assignment',
            self._delete_app_creds_on_assignment_removal)

    def _delete_app_creds_on_user_delete_callback(self, service,
            resource_type, operation, payload):
        user_id = payload['resource_info']
        self.delete_application_credentials_for_user(user_id)

    def _delete_app_creds_on_assignment_removal(self, service,
            resource_type, operation, payload):
        LOG.warn("deleting app cred")
        user_id = payload['resource_info']['user_id']
        project_id = payload['resource_info']['project_id']
        self.delete_application_credentials_for_user_on_project(user_id, project_id)

    def _get_user_roles(self, user_id, project_id):
        assignment_list = self.assignment_api.list_role_assignments(
            user_id=user_id,
            project_id=project_id,
            effective=True)
        return list(set([x['role_id'] for x in assignment_list]))

    def _require_user_has_role_in_project(self, roles, user_id, project_id):
        user_roles = self._get_user_roles(user_id, project_id)
        for role in roles:
            matching_roles = [x for x in user_roles
                              if x == role['id']]
            if not matching_roles:
                raise exception.RoleNotFound(role_id=role['id'])

    def _hash_secret(self, app_cred_ref):
        secret = app_cred_ref['secret']
        app_cred_ref['secret_hash'] = password_hashing.hash_password(secret)
        return app_cred_ref

    def authenticate(self, request, application_credential_id, secret):
        self.driver.authenticate(application_credential_id, secret)

    def create_application_credential(self, application_credential,
                                      initiator=None):
        """Create a new application credential.

        :returns: a new application credential
        """
        user_id = application_credential['user_id']
        trust = {
            'trustor_user_id': user_id,
            'trustee_user_id': user_id,
            'project_id': application_credential['project_id'],
            'impersonation': False
        }
        trust_id = uuid.uuid4().hex
        roles = application_credential.pop('roles', [])
        project_id = application_credential['project_id']
        self._require_user_has_role_in_project(roles, user_id, project_id)
        self.trust_api.create_trust(trust_id, trust, roles,
                                    initiator=initiator)
        application_credential['trust_id'] = trust_id
        self._hash_secret(application_credential)
        unhashed_secret = application_credential.pop('secret')
        ref = self.driver.create_application_credential(
            application_credential)
        ref['roles'] = roles
        ref['secret'] = unhashed_secret
        return ref

    def get_application_credential(self, application_credential_id):
        """Get application credential details.

        :returns: an application credential
        """
        app_cred = self.driver.get_application_credential(
            application_credential_id)
        trust = self.trust_api.get_trust(app_cred['trust_id'])
        app_cred['roles'] = trust.get('roles', [])
        return app_cred

    def list_application_credentials(self, user_id):
        """List application credentials for a user.

        :returns: a plist of application credentials
        """
        return self.driver.list_application_credentials_for_user(user_id)

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
        """
        application_credentials = \
            self.driver.list_application_credentials_for_user(user_id)
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
