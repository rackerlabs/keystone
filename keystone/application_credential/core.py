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

from oslo_log import log

from keystone.common import dependency
from keystone.common import manager
import keystone.conf


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


@dependency.requires('identity_api', 'trust_api')
@dependency.provider('application_credential_api')
class Manager(manager.Manager):
    """Default pivot point for the Application Credential backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.application_credential'

    _APP_CRED = 'application_credential'

    def __init__(self):
        # super(Manager, self).__init__(CONF.application_credential.driver)
        # setup notifications
        pass

    def create_application_credential(self, application_credential,
                                      initiator=None):
        """Create a new application credential.

        :returns: a new application credential
        """
        LOG.info("Creating application credential")
        return {'id': 'test'}

    def get_application_credential(self, application_credential_id):
        """Get application credential details.

        :returns: an application credential
        """
        LOG.info("Getting application credential")
        return {'id': 'test'}

    def list_application_credentials(self, user_id):
        """List application credentials for a user.

        :returns: a plist of application credentials
        """
        LOG.info("Listing application credentials")
        return [{'id': 'test'}]

    def delete_application_credential(self, application_credential_id,
                                      initiator=None):
        """Delete an application credential.

        :raises keystone.exception.ApplicationCredentialNotFound: If the
            application credential doesn't exist.
        """
        LOG.info("Deleting application credential")
