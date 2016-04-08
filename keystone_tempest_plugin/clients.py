# Copyright 2016 Red Hat, Inc.
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

from keystone_tempest_plugin import exceptions
from keystone_tempest_plugin.services.identity.v3 \
    import identity_providers_client
from keystone_tempest_plugin.services.identity.v3 \
    import service_providers_client

from tempest import clients
from tempest.common import credentials_factory as common_creds
from tempest import config

CONF = config.CONF
ADMIN_CREDS = common_creds.get_configured_credentials('identity_admin')

# Only the v3 auth version is supported
SUPPORTED_AUTH_VERSION = 'v3'


class Manager(clients.Manager):

    def __init__(self, credentials=ADMIN_CREDS, service=None):
        super(Manager, self).__init__(credentials, service)

        identity_auth_version = CONF.identity.auth_version
        if identity_auth_version != SUPPORTED_AUTH_VERSION:
            raise exceptions.BadAuthVersionException(
                bad_version=identity_auth_version,
                supported_version=SUPPORTED_AUTH_VERSION)

        self.identity_providers_client = (
            identity_providers_client.IdentityProvidersClient(
                self.auth_provider))

        self.service_providers_client = (
            service_providers_client.ServiceProvidersClient(
                self.auth_provider))
