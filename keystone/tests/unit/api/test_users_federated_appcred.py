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

"""Unit tests for _enforce_federated_app_cred_policy (keystone/api/users.py).

Tests cover all policy branches for federated vs. non-federated tokens
without requiring a full HTTP stack or database.
"""

import datetime
from unittest import mock

from oslo_config import fixture as config_fixture
import testtools
from oslo_utils import timeutils

import keystone.conf
from keystone import exception as ks_exception
from keystone.api.users import _enforce_federated_app_cred_policy

CONF = keystone.conf.CONF


def _make_token(is_federated):
    token = mock.Mock()
    token.is_federated = is_federated
    return token


class TestEnforceFederatedAppCredPolicy(testtools.TestCase):
    """Tests for _enforce_federated_app_cred_policy."""

    def setUp(self):
        super().setUp()
        self.cfg = self.useFixture(config_fixture.Config(CONF))
        # Reset to defaults before each test
        self.cfg.config(
            group='application_credential',
            federated_enabled=True,
            federated_max_duration_days=30,
            federated_allow_unrestricted=False,
        )

    # ------------------------------------------------------------------
    # Non-federated token — all checks must be skipped entirely
    # ------------------------------------------------------------------

    def test_local_token_is_noop(self):
        """Non-federated (local/LDAP) token must not be affected."""
        token = _make_token(is_federated=False)
        data = {}
        _enforce_federated_app_cred_policy(token, data)
        self.assertEqual({}, data)

    def test_local_token_unrestricted_not_blocked(self):
        """Local user can request unrestricted even when federated_allow_unrestricted=False."""
        token = _make_token(is_federated=False)
        data = {'unrestricted': True}
        _enforce_federated_app_cred_policy(token, data)  # must not raise

    # ------------------------------------------------------------------
    # federated_enabled = False
    # ------------------------------------------------------------------

    def test_federated_disabled_raises(self):
        """ForbiddenAction raised when federated_enabled=False."""
        self.cfg.config(
            group='application_credential', federated_enabled=False
        )
        token = _make_token(is_federated=True)
        self.assertRaises(
            ks_exception.ForbiddenAction,
            _enforce_federated_app_cred_policy,
            token,
            {},
        )

    # ------------------------------------------------------------------
    # unrestricted flag
    # ------------------------------------------------------------------

    def test_federated_unrestricted_blocked_by_default(self):
        """ForbiddenAction raised for unrestricted=True when not allowed."""
        token = _make_token(is_federated=True)
        self.assertRaises(
            ks_exception.ForbiddenAction,
            _enforce_federated_app_cred_policy,
            token,
            {'unrestricted': True},
        )

    def test_federated_unrestricted_allowed_when_configured(self):
        """No exception when federated_allow_unrestricted=True."""
        self.cfg.config(
            group='application_credential',
            federated_allow_unrestricted=True,
            federated_max_duration_days=0,
        )
        token = _make_token(is_federated=True)
        data = {'unrestricted': True}
        _enforce_federated_app_cred_policy(token, data)  # must not raise

    # ------------------------------------------------------------------
    # federated_max_duration_days = 0 (unlimited)
    # ------------------------------------------------------------------

    def test_max_duration_zero_allows_any_expiry(self):
        """When max_duration_days=0 no expiry constraint is applied."""
        self.cfg.config(
            group='application_credential', federated_max_duration_days=0
        )
        token = _make_token(is_federated=True)
        far_future = '2099-01-01T00:00:00.000000Z'
        data = {'expires_at': far_future}
        _enforce_federated_app_cred_policy(token, data)
        self.assertEqual(far_future, data['expires_at'])

    def test_max_duration_zero_no_auto_set(self):
        """When max_duration_days=0 and no expires_at, nothing is injected."""
        self.cfg.config(
            group='application_credential', federated_max_duration_days=0
        )
        token = _make_token(is_federated=True)
        data = {}
        _enforce_federated_app_cred_policy(token, data)
        self.assertNotIn('expires_at', data)

    # ------------------------------------------------------------------
    # Auto-setting expires_at from federated_max_duration_days
    # ------------------------------------------------------------------

    def test_no_expires_at_auto_set(self):
        """expires_at is injected automatically when absent (default 30 days)."""
        token = _make_token(is_federated=True)
        data = {}
        before = timeutils.utcnow()
        _enforce_federated_app_cred_policy(token, data)
        after = timeutils.utcnow()

        self.assertIn('expires_at', data)
        auto = timeutils.normalize_time(timeutils.parse_isotime(data['expires_at']))
        self.assertGreaterEqual(auto, before + datetime.timedelta(days=30))
        self.assertLessEqual(auto, after + datetime.timedelta(days=30))

    def test_no_expires_at_auto_set_custom_days(self):
        """Auto-set expiry respects a custom federated_max_duration_days."""
        self.cfg.config(
            group='application_credential', federated_max_duration_days=7
        )
        token = _make_token(is_federated=True)
        data = {}
        before = timeutils.utcnow()
        _enforce_federated_app_cred_policy(token, data)

        auto = timeutils.normalize_time(timeutils.parse_isotime(data['expires_at']))
        self.assertGreaterEqual(auto, before + datetime.timedelta(days=7))
        self.assertLessEqual(auto, before + datetime.timedelta(days=7, seconds=5))

    # ------------------------------------------------------------------
    # expires_at validation against the configured maximum
    # ------------------------------------------------------------------

    def test_expires_at_within_limit_is_accepted(self):
        """expires_at within max_duration_days must not raise."""
        token = _make_token(is_federated=True)
        near = (timeutils.utcnow() + datetime.timedelta(days=10)).strftime(
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        data = {'expires_at': near}
        _enforce_federated_app_cred_policy(token, data)
        self.assertEqual(near, data['expires_at'])

    def test_expires_at_exceeds_limit_raises(self):
        """ValidationError raised when expires_at exceeds max_duration_days."""
        token = _make_token(is_federated=True)
        far = (timeutils.utcnow() + datetime.timedelta(days=60)).strftime(
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        self.assertRaises(
            ks_exception.ValidationError,
            _enforce_federated_app_cred_policy,
            token,
            {'expires_at': far},
        )

    def test_expires_at_exactly_at_limit_is_accepted(self):
        """expires_at equal to the max boundary must be accepted."""
        token = _make_token(is_federated=True)
        # Use 29 days to safely clear any sub-second drift in utcnow() calls.
        boundary = (timeutils.utcnow() + datetime.timedelta(days=29)).strftime(
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        data = {'expires_at': boundary}
        _enforce_federated_app_cred_policy(token, data)
