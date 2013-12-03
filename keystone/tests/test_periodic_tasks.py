# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Deutsche Telekom AG
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

import datetime
import uuid
import time

from keystone import tests
from keystone.openstack.common import timeutils
from keystone.tests import default_fixtures

from keystone import token

from keystone.common import sql
from keystone.common import environment
from keystone.common.periodic_tasks import PeriodicTasks
from keystone.token.backends.sql import TokenModel


class PeriodicTasksTestCase(tests.TestCase, sql.Base):
    def setUp(self):
        super(PeriodicTasksTestCase, self).setUp()
        self.config([tests.etcdir('keystone.conf.sample'),
                     tests.testsdir('test_overrides.conf'),
                     tests.testsdir('backend_sql.conf')])

        self.load_backends()
        environment.use_eventlet(True)
        # create tables and keep an engine reference for cleanup.
        # this must be done after the models are loaded by the managers.
        self.engine = self.get_engine()
        sql.ModelBase.metadata.create_all(bind=self.engine)

        # populate the engine with tables & fixtures
        self.load_fixtures(default_fixtures)

    def test_task_flush_expired_tokens(self):
        token_manager = token.Manager()
        session = token_manager.driver.get_session()
        # token list should be empty
        self.assertEqual(session.query(TokenModel).count(), 0)
        # create a dummy token (already expired)
        token_id = uuid.uuid4().hex
        expire_time = timeutils.utcnow() - datetime.timedelta(seconds=60)
        data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                'expires': expire_time,
                'trust_id': None,
                'user': {'id': 'testuserid'}}
        token_manager.create_token(token_id, data)
        # check that token is in database
        self.assertEqual(session.query(TokenModel).count(), 1)
        # create the periodic task
        PeriodicTasks()
        time.sleep(2)
        # now expired tokens should be flushed
        self.assertEqual(session.query(TokenModel).count(), 0)
