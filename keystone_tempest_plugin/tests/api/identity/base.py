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

import tempest.test


class BaseIdentityV3Test(tempest.test.BaseTestCase):

    credentials = ['primary']

    # identity v3 tests should obtain tokens and create accounts via v3
    # regardless of the configured CONF.identity.auth_version
    identity_version = 'v3'

    @classmethod
    def setup_clients(cls):
        super(BaseIdentityV3Test, cls).setup_clients()

    @classmethod
    def resource_cleanup(cls):
        super(BaseIdentityV3Test, cls).resource_cleanup()


class BaseIdentityV3AdminTest(BaseIdentityV3Test):

    credentials = ['primary', 'admin']

    @classmethod
    def setup_clients(cls):
        super(BaseIdentityV3AdminTest, cls).setup_clients()
        cls.identity_providers_client = cls.os_adm.identity_providers_client

    @classmethod
    def resource_setup(cls):
        super(BaseIdentityV3AdminTest, cls).resource_setup()

    @classmethod
    def resource_cleanup(cls):
        super(BaseIdentityV3AdminTest, cls).resource_cleanup()
