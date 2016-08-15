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

"""Main entry point into the Credential service."""

from oslo_log import versionutils

from keystone.common import dependency
from keystone.common import driver_hints
from keystone.common import manager
import keystone.conf
from keystone.credential.backends import base


CONF = keystone.conf.CONF


@dependency.provider('credential_api')
@dependency.requires('credential_provider_api')
class Manager(manager.Manager):
    """Default pivot point for the Credential backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.credential'

    def __init__(self):
        super(Manager, self).__init__(CONF.credential.driver)

    @manager.response_truncated
    def list_credentials(self, hints=None):
        credentials = self.driver.list_credentials(
            hints or driver_hints.Hints()
        )
        for credential in credentials:
            if CONF.credential.encrypt:
                decrypted_blob = self.credential_provider_api.decrypt(
                    credential['blob']
                )
                credential['blob'] = decrypted_blob
            credential.pop('key_hash', None)
        return credentials

    def get_credential(self, credential_id):
        """Return a credential reference."""
        credential = self.driver.get_credential(credential_id)
        credential.pop('key_hash', None)
        if CONF.credential.encrypt:
            decrypted_blob = self.credential_provider_api.decrypt(
                credential['blob']
            )
            credential['blob'] = decrypted_blob
        return credential

    def create_credential(self, credential_id, credential):
        """Create a credential."""
        credential_copy = credential.copy()
        if CONF.credential.encrypt:
            encrypted_blob = self.credential_provider_api.encrypt(
                credential['blob']
            )
            credential_copy['blob'] = encrypted_blob
            credential_copy['key_hash'] = (
                self.credential_provider_api.primary_key_hash
            )
        ref = self.driver.create_credential(credential_id, credential_copy)
        ref.pop('key_hash', None)
        ref['blob'] = credential['blob']
        return ref

    def update_credential(self, credential_id, credential):
        """Update an existing credential."""
        credential_copy = credential.copy()
        if CONF.credential.encrypt:
            encrypted_blob = self.credential_provider_api.encrypt(
                credential['blob']
            )
            credential_copy['blob'] = encrypted_blob
            credential_copy['key_hash'] = (
                self.credential_provider_api.primary_key_hash
            )
        cred = self.driver.update_credential(credential_id, credential_copy)
        cred.pop('key_hash', None)
        cred['blob'] = credential['blob']
        return cred


@versionutils.deprecated(
    versionutils.deprecated.NEWTON,
    what='keystone.credential.CredentialDriverV8',
    in_favor_of='keystone.credential.backends.base.CredentialDriverV8',
    remove_in=+1)
class AuthMethodHandler(base.CredentialDriverV8):
    pass


Driver = manager.create_legacy_driver(base.CredentialDriverV8)
