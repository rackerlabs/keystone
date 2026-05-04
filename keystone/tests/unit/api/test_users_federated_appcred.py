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

"""Unit tests for app cred policy enforcement (keystone/api/users.py,
keystone/server/__init__.py).

Tests cover:
- _enforce_app_cred_policy: all policy branches for federated/local tokens
- _validate_application_credential_config: startup config validation
"""

import datetime
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as config_fixture
import testtools
from oslo_utils import timeutils

import keystone.conf
from keystone import exception as ks_exception
from keystone.api.users import _enforce_app_cred_policy
from keystone.server import _validate_application_credential_config

CONF = keystone.conf.CONF


def _make_token(is_federated):
    token = mock.Mock()
    token.is_federated = is_federated
    return token


class _AppCredPolicyBase(testtools.TestCase):
    """Shared helpers for app cred policy test classes."""

    IS_FEDERATED = None  # override in subclass

    def setUp(self):
        super().setUp()
        self.cfg = self.useFixture(config_fixture.Config(CONF))
        self._set_defaults()

    def _set_defaults(self):
        raise NotImplementedError

    def _token(self):
        return _make_token(is_federated=self.IS_FEDERATED)

    def _call(self, data):
        return _enforce_app_cred_policy(self._token(), data)

    # ------------------------------------------------------------------
    # Shared test logic (parametrised by subclass config)
    # ------------------------------------------------------------------

    def _test_disabled_raises(self):
        self.assertRaises(ks_exception.ForbiddenAction, self._call, {})

    def _test_unrestricted_blocked(self):
        self.assertRaises(
            ks_exception.ForbiddenAction, self._call, {'unrestricted': True}
        )

    def _test_unrestricted_allowed(self):
        self._call({'unrestricted': True})  # must not raise

    def _test_max_zero_no_constraint(
        self, far_future='2099-01-01T00:00:00.000000Z'
    ):
        data = {'expires_at': far_future}
        self._call(data)
        self.assertEqual(far_future, data['expires_at'])

    def _test_max_zero_no_auto_set(self):
        data = {}
        self._call(data)
        self.assertNotIn('expires_at', data)

    def _test_auto_set(self, expected_days):
        data = {}
        before = timeutils.utcnow()
        self._call(data)
        after = timeutils.utcnow()
        self.assertIn('expires_at', data)
        auto = timeutils.normalize_time(
            timeutils.parse_isotime(data['expires_at'])
        )
        delta = datetime.timedelta(days=expected_days)
        self.assertGreaterEqual(auto, before + delta)
        self.assertLessEqual(auto, after + delta)

    def _test_expires_within_limit(self, days=10):
        near = (timeutils.utcnow() + datetime.timedelta(days=days)).strftime(
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        data = {'expires_at': near}
        self._call(data)
        self.assertEqual(near, data['expires_at'])

    def _test_expires_exceeds_limit(self, days=60):
        far = (timeutils.utcnow() + datetime.timedelta(days=days)).strftime(
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        self.assertRaises(
            ks_exception.ValidationError, self._call, {'expires_at': far}
        )


class TestEnforceFederatedAppCredPolicy(_AppCredPolicyBase):
    """Tests for the federated branch of _enforce_app_cred_policy."""

    IS_FEDERATED = True

    def _set_defaults(self):
        self.cfg.config(
            group='application_credential',
            federated_enabled=True,
            federated_max_duration_days=30,
            federated_allow_unrestricted=False,
        )

    def test_federated_disabled_raises(self):
        """ForbiddenAction raised when federated_enabled=False."""
        self.cfg.config(
            group='application_credential', federated_enabled=False
        )
        self._test_disabled_raises()

    def test_federated_unrestricted_blocked_by_default(self):
        """ForbiddenAction raised for unrestricted=True when not allowed."""
        self._test_unrestricted_blocked()

    def test_federated_unrestricted_allowed_when_configured(self):
        """No exception when federated_allow_unrestricted=True."""
        self.cfg.config(
            group='application_credential',
            federated_allow_unrestricted=True,
            federated_max_duration_days=0,
        )
        self._test_unrestricted_allowed()

    def test_max_duration_zero_allows_any_expiry(self):
        """When federated_max_duration_days=0 no expiry constraint applied."""
        self.cfg.config(
            group='application_credential', federated_max_duration_days=0
        )
        self._test_max_zero_no_constraint()

    def test_max_duration_zero_no_auto_set(self):
        """federated_max_duration_days=0: no expires_at injected."""
        self.cfg.config(
            group='application_credential', federated_max_duration_days=0
        )
        self._test_max_zero_no_auto_set()

    def test_no_expires_at_auto_set(self):
        """expires_at auto-set to 30 days when absent (default)."""
        self._test_auto_set(expected_days=30)

    def test_no_expires_at_auto_set_custom_days(self):
        """Auto-set expiry respects a custom federated_max_duration_days."""
        self.cfg.config(
            group='application_credential', federated_max_duration_days=7
        )
        self._test_auto_set(expected_days=7)

    def test_expires_at_within_limit_is_accepted(self):
        """expires_at +10d within 30d limit must not raise."""
        self._test_expires_within_limit(days=10)

    def test_expires_at_exceeds_limit_raises(self):
        """ValidationError raised when expires_at exceeds federated limit."""
        self._test_expires_exceeds_limit(days=60)

    def test_expires_at_exactly_at_limit_is_accepted(self):
        """expires_at at boundary (29d) must be accepted."""
        self._test_expires_within_limit(days=29)


class TestEnforceLocalAppCredPolicy(_AppCredPolicyBase):
    """Tests for the local/LDAP branch of _enforce_app_cred_policy."""

    IS_FEDERATED = False

    def _set_defaults(self):
        self.cfg.config(
            group='application_credential',
            enabled=True,
            max_duration_days=0,
            allow_unrestricted=True,
        )

    def test_local_default_is_noop(self):
        """Default config (unlimited, unrestricted) must not affect data."""
        data = {}
        self._call(data)
        self.assertEqual({}, data)

    def test_local_disabled_raises(self):
        """ForbiddenAction raised when enabled=False."""
        self.cfg.config(group='application_credential', enabled=False)
        self._test_disabled_raises()

    def test_local_unrestricted_allowed_by_default(self):
        """Local user can create unrestricted app creds by default."""
        self._test_unrestricted_allowed()

    def test_local_unrestricted_blocked_when_configured(self):
        """ForbiddenAction raised when allow_unrestricted=False."""
        self.cfg.config(
            group='application_credential', allow_unrestricted=False
        )
        self._test_unrestricted_blocked()

    def test_local_max_zero_no_constraint(self):
        """Default max_duration_days=0 imposes no expiry constraint."""
        self._test_max_zero_no_constraint()

    def test_local_max_zero_no_auto_set(self):
        """Default max_duration_days=0 does not inject expires_at."""
        self._test_max_zero_no_auto_set()

    def test_local_no_expires_at_auto_set(self):
        """expires_at auto-set when max_duration_days is set."""
        self.cfg.config(
            group='application_credential', max_duration_days=90
        )
        self._test_auto_set(expected_days=90)

    def test_local_expires_at_within_limit_is_accepted(self):
        """expires_at within max_duration_days must not raise."""
        self.cfg.config(
            group='application_credential', max_duration_days=90
        )
        self._test_expires_within_limit(days=30)

    def test_local_expires_at_exceeds_limit_raises(self):
        """ValidationError raised when expires_at exceeds max_duration_days."""
        self.cfg.config(
            group='application_credential', max_duration_days=90
        )
        self._test_expires_exceeds_limit(days=120)

    def test_local_federated_settings_do_not_bleed_over(self):
        """federated_* settings must not affect local token path."""
        self.cfg.config(
            group='application_credential',
            federated_enabled=False,
            federated_allow_unrestricted=False,
            federated_max_duration_days=1,
        )
        data = {'unrestricted': True}
        self._call(data)  # must not raise despite restrictive federated config


class TestValidateApplicationCredentialConfig(testtools.TestCase):
    """Tests for _validate_application_credential_config (startup check)."""

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
            cfg.ConfigFileValueError,
            _validate_application_credential_config,
        )

    def test_default_config_is_valid(self):
        """Default config (federated_enabled=True, 30 days) is valid."""
        _validate_application_credential_config()  # must not raise
