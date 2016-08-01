# Copyright 2016 OpenStack Foundation
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

import uuid

from keystone.common.sql import migration_phase_sql
from keystone import exception
from keystone.tests import unit
from keystone.tests.unit.ksfixtures import database


class MigrationPhaseSqlTests(unit.SQLDriverOverrides, unit.TestCase):

    def setUp(self):
        super(MigrationPhaseSqlTests, self).setUp()
        self.useFixture(database.Database())
        self.migration_phase = migration_phase_sql.MigrationPhase()

    def config_files(self):
        config_files = super(MigrationPhaseSqlTests, self).config_files()
        config_files.append(unit.dirs.tests_conf('backend_sql.conf'))
        return config_files

    def test_crud_phase(self):
        phase = {'current_version': uuid.uuid4().hex,
                 'migrating_to_version': uuid.uuid4().hex,
                 'current_phase': uuid.uuid4().hex}

        # With no row in table, get & update should fail
        self.assertRaises(exception.NotFound,
                          self.migration_phase.get_migration_status)
        self.assertRaises(exception.NotFound,
                          self.migration_phase.update_migration_status,
                          phase)

        ref = self.migration_phase.create_migration_status(phase)
        self.assertEqual(phase, ref)

        update_phase = {'current_phase': uuid.uuid4().hex}
        ref = self.migration_phase.update_migration_status(update_phase)
        phase['current_phase'] = update_phase['current_phase']
        self.assertEqual(phase, ref)

        ref = self.migration_phase.get_migration_status()
        self.assertEqual(phase, ref)
