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

from keystone_tempest_plugin import clients

import tempest.test


class BaseIdentityTest(tempest.test.BaseTestCase):

    # NOTE(rodrigods): for now, all tests are in the admin scope, if
    # necessary another class can be created to handle non-admin tests.
    credentials = ['primary', 'admin']
    identity_version = 'v3'

    @classmethod
    def setup_clients(cls):
        super(BaseIdentityTest, cls).setup_clients()
        keystone_manager = clients.Manager()

        cls.identity_providers_client = (
            keystone_manager.identity_providers_client)
        cls.mapping_rules_client = (
            keystone_manager.mapping_rules_client)
        cls.service_providers_client = (
            keystone_manager.service_providers_client)

    @classmethod
    def resource_setup(cls):
        super(BaseIdentityTest, cls).resource_setup()

    @classmethod
    def resource_cleanup(cls):
        super(BaseIdentityTest, cls).resource_cleanup()
