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

import datetime
import uuid

from oslo_utils import timeutils
import six
from six.moves import http_client
from testtools import matchers

from keystone.common import utils
from keystone.contrib.revoke import model
from keystone.tests.unit import ksfixtures
from keystone.tests.unit import test_v3
from keystone.token import provider


def _future_time_string():
    expire_delta = datetime.timedelta(seconds=1000)
    future_time = timeutils.utcnow() + expire_delta
    return utils.isotime(future_time)


class OSRevokeTests(test_v3.RestfulTestCase, test_v3.JsonHomeTestMixin):
    EXTENSION_NAME = 'revoke'
    EXTENSION_TO_ADD = 'revoke_extension'

    JSON_HOME_DATA = {
        'http://docs.openstack.org/api/openstack-identity/3/ext/OS-REVOKE/1.0/'
        'rel/events': {
            'href': '/OS-REVOKE/events',
        },
    }

    def test_get_empty_list(self):
        resp = self.get('/OS-REVOKE/events')
        self.assertEqual([], resp.json_body['events'])

    def _blank_event(self):
        return {}

    # The two values will be the same with the exception of
    # 'issued_before' which is set when the event is recorded.
    def assertReportedEventMatchesRecorded(self, event, sample, before_time):
        after_time = timeutils.utcnow()
        event_issued_before = timeutils.normalize_time(
            timeutils.parse_isotime(event['issued_before']))
        self.assertTrue(
            before_time <= event_issued_before,
            'invalid event issued_before time; %s is not later than %s.' % (
                utils.isotime(event_issued_before, subsecond=True),
                utils.isotime(before_time, subsecond=True)))
        self.assertTrue(
            event_issued_before <= after_time,
            'invalid event issued_before time; %s is not earlier than %s.' % (
                utils.isotime(event_issued_before, subsecond=True),
                utils.isotime(after_time, subsecond=True)))
        del (event['issued_before'])
        self.assertEqual(sample, event)

    def test_revoked_list_self_url(self):
        revoked_list_url = '/OS-REVOKE/events'
        resp = self.get(revoked_list_url)
        links = resp.json_body['links']
        self.assertThat(links['self'], matchers.EndsWith(revoked_list_url))

    def test_revoked_token_in_list(self):
        user_id = uuid.uuid4().hex
        expires_at = provider.default_expire_time()
        sample = self._blank_event()
        sample['user_id'] = six.text_type(user_id)
        sample['expires_at'] = six.text_type(utils.isotime(expires_at))
        before_time = timeutils.utcnow()
        self.revoke_api.revoke_by_expiration(user_id, expires_at)
        resp = self.get('/OS-REVOKE/events')
        events = resp.json_body['events']
        self.assertEqual(1, len(events))
        self.assertReportedEventMatchesRecorded(events[0], sample, before_time)

    def test_disabled_project_in_list(self):
        project_id = uuid.uuid4().hex
        sample = dict()
        sample['project_id'] = six.text_type(project_id)
        before_time = timeutils.utcnow()
        self.revoke_api.revoke(
            model.RevokeEvent(project_id=project_id))

        resp = self.get('/OS-REVOKE/events')
        events = resp.json_body['events']
        self.assertEqual(1, len(events))
        self.assertReportedEventMatchesRecorded(events[0], sample, before_time)

    def test_disabled_domain_in_list(self):
        domain_id = uuid.uuid4().hex
        sample = dict()
        sample['domain_id'] = six.text_type(domain_id)
        before_time = timeutils.utcnow()
        self.revoke_api.revoke(
            model.RevokeEvent(domain_id=domain_id))

        resp = self.get('/OS-REVOKE/events')
        events = resp.json_body['events']
        self.assertEqual(1, len(events))
        self.assertReportedEventMatchesRecorded(events[0], sample, before_time)

    def test_list_since_invalid(self):
        self.get('/OS-REVOKE/events?since=blah',
                 expected_status=http_client.BAD_REQUEST)

    def test_list_since_valid(self):
        resp = self.get('/OS-REVOKE/events?since=2013-02-27T18:30:59.999999Z')
        events = resp.json_body['events']
        self.assertEqual(0, len(events))

    def test_since_future_time_no_events(self):
        domain_id = uuid.uuid4().hex
        sample = dict()
        sample['domain_id'] = six.text_type(domain_id)

        self.revoke_api.revoke(
            model.RevokeEvent(domain_id=domain_id))

        resp = self.get('/OS-REVOKE/events')
        events = resp.json_body['events']
        self.assertEqual(1, len(events))

        resp = self.get('/OS-REVOKE/events?since=%s' % _future_time_string())
        events = resp.json_body['events']
        self.assertEqual([], events)


class RaceConditions(object):
    """Test race conditions between token creation, revocation and validation.

    Token creation and revocation each involve several timestamps, and both
    sets of timestamps are evaluated at the time of token validation. These
    tests assert the behavior of keystone when those timestamps are nearly
    identical or equal to each other by tightly controlling the clock between
    client-side operations to simulate simultaneous or nearly simultaneous
    requests.

    When considering these three events, we can constrain their sequencing as
    follows:

    - Token validation must always follow token creation, otherwise we have no
      token to validate.

    - A revocation event must always precede token validation, otherwise we can
      safely assume that the token will be valid. Besides, We have plenty of
      tests that validate tokens already.

    Given those constraints, there are two possible orderings of these three
    events that could potentially result in a race condition:

    - Create, Revoke, Validate

    - Revoke, Create, Validate

    Timestamps have finite precision. All possible timestamps of these events
    can be enumerated as follows:

    - Create = Revoke = Validate: All events occur at the same timestamp.

    - Create = Revoke < Validate: Creation and revocation happen at the same
      timestamp, followed by validation.

    - Create < Revoke = Validate: Creation happens first, followed by
      revocation and validation at the same timestamp.

    - Create < Revoke < Validate: Creation happens first, then revocation, then
      validation.

    - Revoke = Create = Validate: All events occur at the same timestamp.

    - Revoke = Create < Validate: Revocation and creation happen at the same
      timestamp, followed by validation.

    - Revoke < Create = Validate: Revocation happens first, followed by
      creation and validation at the same timestamp.

    - Revoke < Create < Validate: Revocation happens first, then creation, then
      validation.

    These comparisons hold true regardless of the precision used in timestamps.
    Ignoring the potential side effects of these operations, two of these
    sequences are mathematically identical. But let's not take that theory for
    granted!

    """
    def create_token(self):
        """Create a token for the test user."""
        r = self.v3_authenticate_token(
            self.build_authentication_request(
                user_id=self.default_domain_user['id'],
                password=self.default_domain_user['password']))
        return r.headers.get('X-Subject-Token')

    def revocation_event(self, token=None):
        """Trigger a revocation event which revokes the test user's tokens."""
        token = token or self.create_token()
        new_password = uuid.uuid4().hex
        self.post(
            '/users/%s/password' % self.default_domain_user['id'],
            body={'user': {
                'password': new_password,
                'original_password': self.default_domain_user['password']}},
            token=token,
            expected_status=http_client.NO_CONTENT)
        self.default_domain_user['password'] = new_password

    def validate_token(self, token, expected_status=http_client.OK):
        """Validate the test user's token."""
        self.head(
            '/auth/tokens',
            headers={'X-Subject-Token': token},
            expected_status=expected_status)

    def setup_time_overrides(self):
        """Every test manipulates the clock to reproduce race conditions."""
        # Time is frozen for all tests, and the clock will only advance when we
        # want it to. This allows us to simulate microsecond-level timestamp
        # collisions and microsecond-level time deltas.
        timeutils.set_time_override()

        # Restore the clock's normal behavior.
        self.addCleanup(timeutils.clear_time_override)

    def advance_time(self):
        """Advance time by the smallest available time delta (1ms)."""
        timeutils.advance_time_delta(datetime.timedelta(microseconds=1))

    def test_create_eq_revoke_eq_validate(self):
        """All three events happen at the exact same time."""
        token = self.create_token()
        self.revocation_event(token)
        self.validate_token(token, expected_status=http_client.NOT_FOUND)

    def test_create_lt_revoke_eq_validate(self):
        token = self.create_token()
        self.advance_time()
        self.revocation_event(token)
        self.validate_token(token, expected_status=http_client.NOT_FOUND)

    def test_create_eq_revoke_lt_validate(self):
        token = self.create_token()
        self.revocation_event(token)
        self.advance_time()
        self.validate_token(token, expected_status=http_client.NOT_FOUND)

    def test_create_lt_revoke_lt_validate(self):
        token = self.create_token()
        self.advance_time()
        self.revocation_event(token)
        self.advance_time()
        self.validate_token(token, expected_status=http_client.NOT_FOUND)

    def test_revoke_eq_create_eq_validate(self):
        self.revocation_event()
        token = self.create_token()
        self.validate_token(token, expected_status=http_client.NOT_FOUND)

    def test_revoke_lt_create_eq_validate(self):
        self.revocation_event()
        self.advance_time()
        token = self.create_token()
        self.validate_token(token, expected_status=http_client.OK)

    def test_revoke_eq_create_lt_validate(self):
        self.revocation_event()
        token = self.create_token()
        self.advance_time()
        self.validate_token(token, expected_status=http_client.NOT_FOUND)

    def test_revoke_lt_create_lt_validate(self):
        token = self.create_token()
        self.revocation_event()
        self.advance_time()
        token = self.create_token()
        self.advance_time()
        self.validate_token(token, expected_status=http_client.OK)


class TestUUIDRaceConditions(test_v3.RestfulTestCase, RaceConditions):
    def setUp(self):
        # NOTE(lbragstad): UUID is the default token provider, so we don't have
        # to override with fixtures.
        super(TestUUIDRaceConditions, self).setUp()
        self.setup_time_overrides()


class TestFernetRaceConditions(test_v3.RestfulTestCase, RaceConditions):
    def setUp(self):
        super(TestFernetRaceConditions, self).setUp()
        self.setup_time_overrides()

    def advance_time_one_second(self):
        """Advance time by one second."""
        timeutils.advance_time_delta(datetime.timedelta(seconds=2))

    def config_overrides(self):
        super(TestFernetRaceConditions, self).config_overrides()
        self.config_fixture.config(group='token', provider='fernet')
        self.useFixture(ksfixtures.KeyRepository(self.config_fixture))

    def test_create_lt_revoke_eq_validate(self):
        token = self.create_token()
        self.advance_time_one_second()
        self.revocation_event(token)
        # FIXME(lbragstad): This is transient with Fernet. This should return a
        # 404 but it sometimes returns a 200.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))

    def test_revoke_lt_create_eq_validate(self):
        self.revocation_event()
        self.advance_time_one_second()
        token = self.create_token()
        # FIXME(lbragstad): This is transient with Fernet. This should always
        # return 200 but it will sometimes return 404.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))

    def test_revoke_lt_create_lt_validate(self):
        token = self.create_token()
        self.advance_time_one_second()
        self.revocation_event()
        self.advance_time_one_second()
        token = self.create_token()
        self.advance_time_one_second()
        # FIXME(lbragstad): This is transient with Fernet. This should always
        # return a 200 but it will sometimes return 404.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))

    def test_revoke_eq_create_lt_validate(self):
        self.revocation_event()
        token = self.create_token()
        self.advance_time()
        # FIXME(lbragstad): This is transient with Fernet. This should always
        # return a 404 but it will sometimes return 200.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))

    def test_create_eq_revoke_lt_validate(self):
        token = self.create_token()
        self.revocation_event(token)
        self.advance_time()
        # FIXME(lbragstad): This is transient with Fernet. This should always
        # return a 404 but it will sometimes return 200.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))

    def test_create_eq_revoke_eq_validate(self):
        """All three events happen at the exact same time."""
        token = self.create_token()
        self.revocation_event(token)
        # FIXME(lbragstad): This is transient with Fernet. This should always
        # return a 404 but it will sometimes return 200.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))

    def test_create_lt_revoke_lt_validate(self):
        token = self.create_token()
        self.advance_time()
        self.revocation_event(token)
        self.advance_time()
        # FIXME(lbragstad): This is transient with Fernet. This should always
        # return a 404 but it will sometimes return 200.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))

    def test_revoke_eq_create_eq_validate(self):
        self.revocation_event()
        token = self.create_token()
        # FIXME(lbragstad): This is transient with Fernet. This should always
        # return a 404 but it will sometimes return 200.
        self.validate_token(token, expected_status=(
            http_client.OK, http_client.NOT_FOUND))
