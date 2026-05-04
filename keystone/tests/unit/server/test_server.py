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

"""Unit tests for startup config validation (keystone/server/__init__.py)."""

from oslo_config import cfg
from oslo_config import fixture as config_fixture
import testtools

import keystone.conf
from keystone.server import _validate_application_credential_config

CONF = keystone.conf.CONF


class TestValidateApplicationCredentialConfig(testtools.TestCase):
    """Tests for _validate_application_credential_config."""

    def setUp(self):
        super().setUp()
        self.cfg = self.useFixture(config_fixture.Config(CONF))

    def test_valid_config_federated_enabled_with_max_days(self):
        """federated_enabled=True + max_duration_days>0 is valid."""
        self.cfg.config(
            group='application_credential',
            federated_enabled=True,
            federated_max_duration_days=30,
        )
        _validate_application_credential_config()  # must not raise

    def test_valid_config_federated_disabled(self):
        """federated_enabled=False + max_duration_days=0 is valid."""
        self.cfg.config(
            group='application_credential',
            federated_enabled=False,
            federated_max_duration_days=0,
        )
        _validate_application_credential_config()  # must not raise

    def test_invalid_config_raises(self):
        """federated_enabled=True + max_duration_days=0 refuses to start."""
        self.cfg.config(
            group='application_credential',
            federated_enabled=True,
            federated_max_duration_days=0,
        )
        self.assertRaises(
            cfg.ConfigFileValueError, _validate_application_credential_config
        )

    def test_default_config_is_valid(self):
        """Default config (federated_enabled=True, 30 days) is valid."""
        _validate_application_credential_config()  # must not raise
