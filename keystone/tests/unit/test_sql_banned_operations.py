# Copyright 2015 OpenStack Foundation
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


import os

import fixtures
from migrate.versioning import repository
from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
import sqlalchemy
import testtools

from keystone.common.sql import migrate_repo


class DBNotAllowed(Exception):
    pass


class BannedDBSchemaOperations(fixtures.Fixture):
    """Ban some operations for migrations"""

    def __init__(self, banned_resources=None):
        super(BannedDBSchemaOperations, self).__init__()
        self._banned_resources = banned_resources or []

    @staticmethod
    def _explode(resource, op):
        raise DBNotAllowed(
            'Operation %s.%s() is not allowed in a database migration' % (
                resource, op))

    def setUp(self):
        super(BannedDBSchemaOperations, self).setUp()
        for thing in self._banned_resources:
            self.useFixture(fixtures.MonkeyPatch(
                'sqlalchemy.%s.drop' % thing,
                lambda *a, **k: self._explode(thing, 'drop')))
            self.useFixture(fixtures.MonkeyPatch(
                'sqlalchemy.%s.alter' % thing,
                lambda *a, **k: self._explode(thing, 'alter')))


class TestBannedDBSchemaOperations(testtools.TestCase):
    def test_column(self):
        column = sqlalchemy.Column()
        with BannedDBSchemaOperations(['Column']):
            self.assertRaises(DBNotAllowed, column.drop)
            self.assertRaises(DBNotAllowed, column.alter)

    def test_table(self):
        table = sqlalchemy.Table()
        with BannedDBSchemaOperations(['Table']):
            self.assertRaises(DBNotAllowed, table.drop)
            self.assertRaises(DBNotAllowed, table.alter)


class KeystoneMigrationsCheckers(test_migrations.WalkVersionsMixin):
    """Walk over and test all sqlalchemy-migrate migrations."""

    snake_walk = False
    downgrade = False

    @property
    def INIT_VERSION(self):
        return migrate_repo.DB_INIT_VERSION

    @property
    def REPOSITORY(self):
        migrate_file = migrate_repo.__file__
        return repository.Repository(
            os.path.abspath(os.path.dirname(migrate_file))
        )

    @property
    def migration_api(self):
        temp = __import__('oslo_db.sqlalchemy.migration', globals(),
                          locals(), ['versioning_api'], 0)
        return temp.versioning_api

    @property
    def migrate_engine(self):
        return self.engine

    def migrate_up(self, version, with_data=False):
        """Check that migrations don't cause downtime.

        Schema migrations can be done online, allowing for rolling upgrades.
        """
        # NOTE(xek): This is a list of migrations where we allow dropping
        # things. The rules for adding exceptions are very specific:
        #   1) migrations which don't cause incompatibilities are allowed
        #      f.ex. dropping an index or constraint
        #   2) migrations removing structures not used in the previous version
        #      are allowed (we keep compatibility between releases), ex.:
        #        a) feature is deprecated in Kilo
        #        b) code supporting the feature is removed in Liberty
        #        c) table can be dropped only after liberty i.e. in Mitaka
        #   3) any other changes which don't pass this test are disallowed
        exceptions = [
            67,  # drop index (example)
        ]
        # NOTE(xek): Reviewers: DO NOT ALLOW THINGS TO BE ADDED HERE

        # NOTE(xek): We start requiring things be additive in Mitaka,
        # so ignore all migrations before that point.
        MITAKA_START = 81

        if version >= MITAKA_START and version not in exceptions:
            banned = ['Table', 'Column']
        else:
            banned = None
        with BannedDBSchemaOperations(banned):
            super(KeystoneMigrationsCheckers,
                  self).migrate_up(version, with_data)

    def test_walk_versions(self):
        self.walk_versions(self.snake_walk, self.downgrade)


class TestKeystoneMigrationsMySQL(
        KeystoneMigrationsCheckers, test_base.MySQLOpportunisticTestCase):
    pass


class TestKeystoneMigrationsPostgreSQL(
        KeystoneMigrationsCheckers, test_base.PostgreSQLOpportunisticTestCase):
    pass


class TestKeystoneMigrationsSQLite(
        KeystoneMigrationsCheckers, test_base.DbTestCase):
    pass
