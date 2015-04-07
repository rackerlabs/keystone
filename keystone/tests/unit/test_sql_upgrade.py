# Copyright 2012 OpenStack Foundation
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
"""
To run these tests against a live database:

1. Modify the file ``keystone/tests/unit/config_files/backend_sql.conf`` to use
   the connection for your live database.
2. Set up a blank, live database
3. Run the tests using::

    tox -e py27 -- keystone.tests.unit.test_sql_upgrade

WARNING::

    Your database will be wiped.

    Do not do this against a database with valuable data as
    all data will be lost.
"""

import json
import os
import uuid

from migrate.versioning import api as versioning_api
from migrate.versioning import repository as migrate_repository
from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_db.sqlalchemy import migration
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
from oslo_db.sqlalchemy import utils as db_utils
import six
from sqlalchemy.engine import reflection
import sqlalchemy.exc
from sqlalchemy import schema

from keystone.common import sql
from keystone.common.sql import migrate_repo
from keystone.common.sql import migration_helpers
from keystone.contrib import federation
from keystone.contrib import revoke
from keystone import exception
from keystone.tests import unit as tests
from keystone.tests.unit.ksfixtures import database


CONF = cfg.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id

# NOTE(morganfainberg): This should be updated when each DB migration collapse
# is done to mirror the expected structure of the DB in the format of
# { <DB_TABLE_NAME>: [<COLUMN>, <COLUMN>, ...], ... }
INITIAL_TABLE_STRUCTURE = {
    'credential': [
        'id', 'user_id', 'project_id', 'blob', 'type', 'extra',
    ],
    'domain': [
        'id', 'name', 'enabled', 'extra',
    ],
    'endpoint': [
        'id', 'legacy_endpoint_id', 'interface', 'region', 'service_id', 'url',
        'enabled', 'extra',
    ],
    'group': [
        'id', 'domain_id', 'name', 'description', 'extra',
    ],
    'policy': [
        'id', 'type', 'blob', 'extra',
    ],
    'project': [
        'id', 'name', 'extra', 'description', 'enabled', 'domain_id',
    ],
    'role': [
        'id', 'name', 'extra',
    ],
    'service': [
        'id', 'type', 'extra', 'enabled',
    ],
    'token': [
        'id', 'expires', 'extra', 'valid', 'trust_id', 'user_id',
    ],
    'trust': [
        'id', 'trustor_user_id', 'trustee_user_id', 'project_id',
        'impersonation', 'deleted_at', 'expires_at', 'remaining_uses', 'extra',
    ],
    'trust_role': [
        'trust_id', 'role_id',
    ],
    'user': [
        'id', 'name', 'extra', 'password', 'enabled', 'domain_id',
        'default_project_id',
    ],
    'user_group_membership': [
        'user_id', 'group_id',
    ],
    'region': [
        'id', 'description', 'parent_region_id', 'extra',
    ],
    'assignment': [
        'type', 'actor_id', 'target_id', 'role_id', 'inherited',
    ],
}


INITIAL_EXTENSION_TABLE_STRUCTURE = {
    'revocation_event': [
        'id', 'domain_id', 'project_id', 'user_id', 'role_id',
        'trust_id', 'consumer_id', 'access_token_id',
        'issued_before', 'expires_at', 'revoked_at', 'audit_id',
        'audit_chain_id',
    ],
}

EXTENSIONS = {'federation': federation,
              'revoke': revoke}


class SqlMigrateBase(tests.SQLDriverOverrides, tests.TestCase):
    def initialize_sql(self):
        self.metadata = sqlalchemy.MetaData()
        self.metadata.bind = self.engine

    def config_files(self):
        config_files = super(SqlMigrateBase, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_sql.conf'))
        return config_files

    def repo_package(self):
        return sql

    def setUp(self):
        super(SqlMigrateBase, self).setUp()
        database.initialize_sql_session()
        conn_str = CONF.database.connection
        if (conn_str != tests.IN_MEM_DB_CONN_STRING and
                conn_str.startswith('sqlite') and
                conn_str[10:] == tests.DEFAULT_TEST_DB_FILE):
            # Override the default with a DB that is specific to the migration
            # tests only if the DB Connection string is the same as the global
            # default. This is required so that no conflicts occur due to the
            # global default DB already being under migrate control. This is
            # only needed if the DB is not-in-memory
            db_file = tests.dirs.tmp('keystone_migrate_test.db')
            self.config_fixture.config(
                group='database',
                connection='sqlite:///%s' % db_file)

        # create and share a single sqlalchemy engine for testing
        self.engine = sql.get_engine()
        self.Session = db_session.get_maker(self.engine, autocommit=False)

        self.initialize_sql()
        self.repo_path = migration_helpers.find_migrate_repo(
            self.repo_package())
        self.schema = versioning_api.ControlledSchema.create(
            self.engine,
            self.repo_path, self.initial_db_version)

        # auto-detect the highest available schema version in the migrate_repo
        self.max_version = self.schema.repository.version().version

    def tearDown(self):
        sqlalchemy.orm.session.Session.close_all()
        meta = sqlalchemy.MetaData()
        meta.bind = self.engine
        meta.reflect(self.engine)

        with self.engine.begin() as conn:
            inspector = reflection.Inspector.from_engine(self.engine)
            metadata = schema.MetaData()
            tbs = []
            all_fks = []

            for table_name in inspector.get_table_names():
                fks = []
                for fk in inspector.get_foreign_keys(table_name):
                    if not fk['name']:
                        continue
                    fks.append(
                        schema.ForeignKeyConstraint((), (), name=fk['name']))
                table = schema.Table(table_name, metadata, *fks)
                tbs.append(table)
                all_fks.extend(fks)

            for fkc in all_fks:
                conn.execute(schema.DropConstraint(fkc))

            for table in tbs:
                conn.execute(schema.DropTable(table))

        sql.cleanup()
        super(SqlMigrateBase, self).tearDown()

    def select_table(self, name):
        table = sqlalchemy.Table(name,
                                 self.metadata,
                                 autoload=True)
        s = sqlalchemy.select([table])
        return s

    def assertTableExists(self, table_name):
        try:
            self.select_table(table_name)
        except sqlalchemy.exc.NoSuchTableError:
            raise AssertionError('Table "%s" does not exist' % table_name)

    def assertTableDoesNotExist(self, table_name):
        """Asserts that a given table exists cannot be selected by name."""
        # Switch to a different metadata otherwise you might still
        # detect renamed or dropped tables
        try:
            temp_metadata = sqlalchemy.MetaData()
            temp_metadata.bind = self.engine
            sqlalchemy.Table(table_name, temp_metadata, autoload=True)
        except sqlalchemy.exc.NoSuchTableError:
            pass
        else:
            raise AssertionError('Table "%s" already exists' % table_name)

    def upgrade(self, *args, **kwargs):
        self._migrate(*args, **kwargs)

    def _migrate(self, version, repository=None, downgrade=False,
                 current_schema=None):
        repository = repository or self.repo_path
        err = ''
        version = versioning_api._migrate_version(self.schema,
                                                  version,
                                                  not downgrade,
                                                  err)
        if not current_schema:
            current_schema = self.schema
        changeset = current_schema.changeset(version)
        for ver, change in changeset:
            self.schema.runchange(ver, change, changeset.step)
        self.assertEqual(self.schema.version, version)

    def assertTableColumns(self, table_name, expected_cols):
        """Asserts that the table contains the expected set of columns."""
        self.initialize_sql()
        table = self.select_table(table_name)
        actual_cols = [col.name for col in table.columns]
        # Check if the columns are equal, but allow for a different order,
        # which might occur after an upgrade followed by a downgrade
        self.assertItemsEqual(expected_cols, actual_cols,
                              '%s table' % table_name)

    @property
    def initial_db_version(self):
        return getattr(self, '_initial_db_version', 0)


class SqlUpgradeTests(object):

    @property
    def INIT_VERSION(self):
        return migrate_repo.DB_INIT_VERSION

    @property
    def REPOSITORY(self):
        return migrate_repository.Repository(
            os.path.abspath(os.path.dirname(migrate_repo.__file__)))

    @property
    def migration_api(self):
        return versioning_api

    @property
    def migrate_engine(self):
        return self.engine

    def setUp(self):
        super(SqlUpgradeTests, self).setUp()

        database.initialize_sql_session(connection=self.engine.url)
        self.addCleanup(CONF.reset)

        self.Session = db_session.get_maker(self.engine, autocommit=False)

    def assertTableDoesNotExist(self, table_name):
        """Asserts that a given table exists cannot be selected by name."""
        try:
            db_utils.get_table(self.migrate_engine, table_name)
        except sqlalchemy.exc.NoSuchTableError:
            pass
        else:
            raise AssertionError('Table "%s" already exists' % table_name)

    def assertTableColumns(self, table_name, expected_cols):
        """Asserts that the table contains the expected set of columns."""
        table = db_utils.get_table(self.engine, table_name)
        actual_cols = [col.name for col in table.columns]
        # Check if the columns are equal, but allow for a different order,
        # which might occur after an upgrade followed by a downgrade
        self.assertItemsEqual(expected_cols, actual_cols,
                              '%s table' % table_name)

    def assertTableExists(self, table_name):
        try:
            db_utils.get_table(self.migrate_engine, table_name)
        except sqlalchemy.exc.NoSuchTableError:
            raise AssertionError('Table "%s" does not exist' % table_name)

    def test_walk_versions(self):
        self.walk_versions(snake_walk=False, downgrade=False)

    def test_blank_db_to_start(self):
        self.assertTableDoesNotExist('user')

    def test_start_version_db_init_version(self):
        version = migration.db_version(self.engine, self.REPOSITORY.path,
                                       migrate_repo.DB_INIT_VERSION)
        self.assertEqual(
            migrate_repo.DB_INIT_VERSION,
            version,
            'DB is not at version %s' % migrate_repo.DB_INIT_VERSION)

    def _check_044(self, engine, data):
        # check_initial_table_structure
        for table in INITIAL_TABLE_STRUCTURE:
            self.assertTableColumns(table, INITIAL_TABLE_STRUCTURE[table])

        # Ensure the default domain was properly created.
        default_domain = migration_helpers.get_default_domain()

        meta = sqlalchemy.MetaData()
        meta.bind = self.engine

        domain_table = sqlalchemy.Table('domain', meta, autoload=True)

        session = self.Session()
        q = session.query(domain_table)
        refs = q.all()

        self.assertEqual(1, len(refs))
        for k in default_domain.keys():
            self.assertEqual(default_domain[k], getattr(refs[0], k))

    def insert_dict(self, session, table_name, d, table=None):
        """Naively inserts key-value pairs into a table, given a dictionary."""
        if table is None:
            this_table = db_utils.get_table(self.migrate_engine, table_name)
        else:
            this_table = table
        insert = this_table.insert().values(**d)
        session.execute(insert)
        session.commit()

    def _pre_upgrade_051(self, engine):
        self.assertTableDoesNotExist('id_mapping')

    def _check_051(self, engine, data):
        self.assertTableExists('id_mapping')

    def _check_052(self, engine, data):
        self.assertTableColumns('region',
                                ['id', 'description', 'parent_region_id',
                                 'extra', 'url'])

    def _pre_upgrade_053(self, engine):
        session = self.Session()
        _small_region_name = '0' * 30
        _long_region_name = '0' * 255
        _clashing_region_name = '0' * 70

        def add_service():
            service_id = uuid.uuid4().hex

            service = {
                'id': service_id,
                'type': uuid.uuid4().hex
            }

            self.insert_dict(session, 'service', service)

            return service_id

        def add_endpoint(service_id, region):
            endpoint_id = uuid.uuid4().hex

            endpoint = {
                'id': endpoint_id,
                'interface': uuid.uuid4().hex[:8],
                'service_id': service_id,
                'url': uuid.uuid4().hex,
                'region': region
            }
            self.insert_dict(session, 'endpoint', endpoint)

            return endpoint_id

        _service_id_ = add_service()
        add_endpoint(_service_id_, region=_long_region_name)
        add_endpoint(_service_id_, region=_long_region_name)
        add_endpoint(_service_id_, region=_clashing_region_name)
        add_endpoint(_service_id_, region=_small_region_name)
        add_endpoint(_service_id_, region=None)

        # upgrade to 53
        session.close()

    def _check_053(self, engine, data):
        self.assertTableColumns('endpoint',
                                ['id', 'legacy_endpoint_id', 'interface',
                                 'service_id', 'url', 'extra', 'enabled',
                                 'region_id'])

        region_table = db_utils.get_table(self.migrate_engine, 'region')
        self.assertEqual(255, region_table.c.id.type.length)
        self.assertEqual(255, region_table.c.parent_region_id.type.length)
        endpoint_table = db_utils.get_table(self.engine, 'endpoint')
        self.assertEqual(255, endpoint_table.c.region_id.type.length)

        _small_region_name = '0' * 30
        _long_region_name = '0' * 255
        _clashing_region_name = '0' * 70

        session = self.Session()

        region_table = db_utils.get_table(self.migrate_engine, 'region')
        self.assertEqual(1, session.query(region_table).
                         filter_by(id=_long_region_name).count())
        self.assertEqual(1, session.query(region_table).
                         filter_by(id=_clashing_region_name).count())
        self.assertEqual(1, session.query(region_table).
                         filter_by(id=_small_region_name).count())

        endpoint_table = db_utils.get_table(self.migrate_engine, 'endpoint')
        self.assertEqual(5, session.query(endpoint_table).count())
        self.assertEqual(2, session.query(endpoint_table).
                         filter_by(region_id=_long_region_name).count())
        self.assertEqual(1, session.query(endpoint_table).
                         filter_by(region_id=_clashing_region_name).count())
        self.assertEqual(1, session.query(endpoint_table).
                         filter_by(region_id=_small_region_name).count())
        session.close()

    def _check_054(self, engine, data):
        table = db_utils.get_table(self.migrate_engine, 'assignment')
        index_data = [(idx.name, idx.columns.keys()) for idx in table.indexes]
        self.assertIn(('ix_actor_id', ['actor_id']), index_data)

    def _check_055(self, engine, data):
        table = db_utils.get_table(self.migrate_engine, 'token')
        index_data = [(idx.name, idx.columns.keys()) for idx in table.indexes]
        self.assertIn(('ix_token_user_id', ['user_id']), index_data)
        self.assertIn(('ix_token_trust_id', ['trust_id']), index_data)

    def _check_061(self, engine, data):
        self.assertTableColumns('project',
                                ['id', 'name', 'extra', 'description',
                                 'enabled', 'domain_id', 'parent_id'])

    def _pre_upgrade_062(self, engine):
        self.assertTrue(self.does_fk_exist('assignment', 'role_id'))

    def _check_062(self, engine, data):
        if self.engine.name != 'sqlite':
            # sqlite does not support FK deletions (or enforcement)
            self.assertFalse(self.does_fk_exist('assignment', 'role_id'))

    def does_fk_exist(self, table, fk_column):
        inspector = reflection.Inspector.from_engine(self.migrate_engine)
        for fk in inspector.get_foreign_keys(table):
            if fk_column in fk['constrained_columns']:
                return True
        return False

    def _check_063(self, engine, data):
        self.assertTableColumns('region',
                                ['id', 'description', 'parent_region_id',
                                 'extra'])

    def _pre_upgrade_064(self, engine):
        self.assertTrue(self.does_fk_exist('group', 'domain_id'))
        self.assertTrue(self.does_fk_exist('user', 'domain_id'))

    def _check_064(self, engine, data):
        if self.engine.name != 'sqlite':
            # sqlite does not support FK deletions (or enforcement)
            self.assertFalse(self.does_fk_exist('group', 'domain_id'))
            self.assertFalse(self.does_fk_exist('user', 'domain_id'))

    def _pre_upgrade_065(self, engine):
        whitelisted_table = 'whitelisted_config'
        sensitive_table = 'sensitive_config'
        self.assertTableDoesNotExist(whitelisted_table)
        self.assertTableDoesNotExist(sensitive_table)

    def _check_065(self, engine, data):
        whitelisted_table = 'whitelisted_config'
        sensitive_table = 'sensitive_config'
        self.assertTableColumns(whitelisted_table,
                                ['domain_id', 'group', 'option', 'value'])
        self.assertTableColumns(sensitive_table,
                                ['domain_id', 'group', 'option', 'value'])

    def _pre_upgrade_066(self, engine):
        """Update service name data from `extra` to empty string."""
        def add_service(**extra_data):
            service_id = uuid.uuid4().hex

            service = {
                'id': service_id,
                'type': uuid.uuid4().hex,
                'extra': json.dumps(extra_data),
            }

            self.insert_dict(session, 'service', service)

            return service_id

        session = self.Session()

        # Services with extra values having a random attribute and
        # different combinations of name
        random_attr_name = uuid.uuid4().hex
        random_attr_value = uuid.uuid4().hex
        random_attr_str = "%s='%s'" % (random_attr_name, random_attr_value)
        random_attr_no_name = {random_attr_name: random_attr_value}
        random_attr_no_name_str = "%s='%s'" % (random_attr_name,
                                               random_attr_value)
        random_attr_name_value = {random_attr_name: random_attr_value,
                                  'name': 'myname'}
        random_attr_name_value_str = 'name=myname,%s' % random_attr_str
        random_attr_name_empty = {random_attr_name: random_attr_value,
                                  'name': ''}
        random_attr_name_empty_str = 'name=,%s' % random_attr_str
        random_attr_name_none = {random_attr_name: random_attr_value,
                                 'name': None}
        random_attr_name_none_str = 'name=None,%s' % random_attr_str

        services = [
            (add_service(**random_attr_no_name),
             random_attr_name_empty, random_attr_no_name_str),
            (add_service(**random_attr_name_value),
             random_attr_name_value, random_attr_name_value_str),
            (add_service(**random_attr_name_empty),
             random_attr_name_empty, random_attr_name_empty_str),
            (add_service(**random_attr_name_none),
             random_attr_name_empty, random_attr_name_none_str),
        ]

        # NOTE(viktors): Add a service with empty extra field
        self.insert_dict(session, 'service',
                         {'id': uuid.uuid4().hex, 'type': uuid.uuid4().hex})

        session.close()
        return services

    def _check_066(self, engine, data):
        services = data
        session = self.Session()

        # Verify that the services have the expected values.
        service_table = db_utils.get_table(self.migrate_engine, 'service')

        def fetch_service_extra(service_id):
            cols = [service_table.c.extra]
            f = service_table.c.id == service_id
            s = sqlalchemy.select(cols).where(f)
            service = session.execute(s).fetchone()
            return json.loads(service.extra)

        for service_id, exp_extra, msg in services:
            extra = fetch_service_extra(service_id)
            self.assertDictEqual(exp_extra, extra, msg)
        session.close()

    def _does_index_exist(self, table_name, index_name):
        table = db_utils.get_table(self.migrate_engine, table_name)
        return index_name in [idx.name for idx in table.indexes]

    def _pre_upgrade_067(self, engine):
        if self.engine.name == "mysql":
            self.assertTrue(self._does_index_exist('assignment',
                                                   'assignment_role_id_fkey'))

    def _check_067(self, engine, data):
        if self.engine.name == "mysql":
            self.assertFalse(self._does_index_exist('assignment',
                                                    'assignment_role_id_fkey'))


class TestSqlUpgradeSQLite(SqlUpgradeTests,
                           test_migrations.WalkVersionsMixin,
                           test_base.DbTestCase):
    """Run migration tests on SQLite."""


class TestSqlUpgradePostgreSQL(SqlUpgradeTests,
                               test_migrations.WalkVersionsMixin,
                               test_base.PostgreSQLOpportunisticTestCase):
    """Run migration tests on PostgreSQL."""


class TestSqlUpgradeMySQL(SqlUpgradeTests,
                          test_migrations.WalkVersionsMixin,
                          test_base.MySQLOpportunisticTestCase):
    """Run migration tests on MySQL."""

    def test_all_tables_innodb(self):

        self.skipTest('Non-InnoDB tables exists')

        migration_helpers.sync_database_to_version()

        database = self.engine.url.database

        connection = self.engine.connect()
        # sanity check
        total = connection.execute("SELECT count(*) "
                                   "from information_schema.TABLES "
                                   "where TABLE_SCHEMA='%(database)s'" %
                                   dict(database=database))

        self.assertTrue(total.scalar() > 0, "No tables found. Wrong schema?")

        noninnodb = connection.execute("SELECT table_name "
                                       "from information_schema.TABLES "
                                       "where TABLE_SCHEMA='%(database)s' "
                                       "and ENGINE!='InnoDB' "
                                       "and TABLE_NAME!='migrate_version'" %
                                       dict(database=database))
        names = [x[0] for x in noninnodb]
        self.assertEqual([], names,
                         "Non-InnoDB tables exist")

        connection.close()


class VersionTests(SqlMigrateBase):

    _initial_db_version = migrate_repo.DB_INIT_VERSION

    def test_core_initial(self):
        """Get the version before migrated, it's the initial DB version."""
        version = migration_helpers.get_db_version()
        self.assertEqual(migrate_repo.DB_INIT_VERSION, version)

    def test_core_max(self):
        """When get the version after upgrading, it's the new version."""
        self.upgrade(self.max_version)
        version = migration_helpers.get_db_version()
        self.assertEqual(self.max_version, version)

    def test_assert_not_schema_downgrade(self):
        self.upgrade(self.max_version)
        self.assertRaises(
            db_exception.DbMigrationError,
            migration_helpers._sync_common_repo,
            self.max_version - 1)

    def test_extension_not_controlled(self):
        """When get the version before controlling, raises DbMigrationError."""
        self.assertRaises(db_exception.DbMigrationError,
                          migration_helpers.get_db_version,
                          extension='federation')

    def test_extension_initial(self):
        """When get the initial version of an extension, it's 0."""
        for name, extension in six.iteritems(EXTENSIONS):
            abs_path = migration_helpers.find_migrate_repo(extension)
            migration.db_version_control(sql.get_engine(), abs_path)
            version = migration_helpers.get_db_version(extension=name)
            self.assertEqual(0, version,
                             'Migrate version for %s is not 0' % name)

    def test_extension_migrated(self):
        """When get the version after migrating an extension, it's not 0."""
        for name, extension in six.iteritems(EXTENSIONS):
            abs_path = migration_helpers.find_migrate_repo(extension)
            migration.db_version_control(sql.get_engine(), abs_path)
            migration.db_sync(sql.get_engine(), abs_path)
            version = migration_helpers.get_db_version(extension=name)
            self.assertTrue(
                version > 0,
                "Version for %s didn't change after migrated?" % name)
            # Verify downgrades cannot occur
            self.assertRaises(
                db_exception.DbMigrationError,
                migration_helpers._sync_extension_repo,
                extension=name,
                version=0)

    def test_extension_federation_upgraded_values(self):
        abs_path = migration_helpers.find_migrate_repo(federation)
        migration.db_version_control(sql.get_engine(), abs_path)
        migration.db_sync(sql.get_engine(), abs_path, version=6)
        idp_table = sqlalchemy.Table("identity_provider",
                                     self.metadata,
                                     autoload=True)
        idps = [{'id': uuid.uuid4().hex,
                 'enabled': True,
                 'description': uuid.uuid4().hex,
                 'remote_id': uuid.uuid4().hex},
                {'id': uuid.uuid4().hex,
                 'enabled': True,
                 'description': uuid.uuid4().hex,
                 'remote_id': uuid.uuid4().hex}]
        for idp in idps:
            ins = idp_table.insert().values({'id': idp['id'],
                                             'enabled': idp['enabled'],
                                             'description': idp['description'],
                                             'remote_id': idp['remote_id']})
            self.engine.execute(ins)
        migration.db_sync(sql.get_engine(), abs_path)
        idp_remote_ids_table = sqlalchemy.Table("idp_remote_ids",
                                                self.metadata,
                                                autoload=True)
        for idp in idps:
            s = idp_remote_ids_table.select().where(
                idp_remote_ids_table.c.idp_id == idp['id'])
            remote = self.engine.execute(s).fetchone()
            self.assertEqual(idp['remote_id'],
                             remote['remote_id'],
                             'remote_ids must be preserved during the '
                             'migration from identity_provider table to '
                             'idp_remote_ids table')

    def test_unexpected_extension(self):
        """The version for an extension that doesn't exist raises ImportError.

        """

        extension_name = uuid.uuid4().hex
        self.assertRaises(ImportError,
                          migration_helpers.get_db_version,
                          extension=extension_name)

    def test_unversioned_extension(self):
        """The version for extensions without migrations raise an exception.

        """

        self.assertRaises(exception.MigrationNotProvided,
                          migration_helpers.get_db_version,
                          extension='admin_crud')

    def test_initial_with_extension_version_None(self):
        """When performing a default migration, also migrate extensions."""
        migration_helpers.sync_database_to_version(extension=None,
                                                   version=None)
        for table in INITIAL_EXTENSION_TABLE_STRUCTURE:
            self.assertTableColumns(table,
                                    INITIAL_EXTENSION_TABLE_STRUCTURE[table])

    def test_initial_with_extension_version_max(self):
        """When migrating to max version, do not migrate extensions."""
        migration_helpers.sync_database_to_version(extension=None,
                                                   version=self.max_version)
        for table in INITIAL_EXTENSION_TABLE_STRUCTURE:
            self.assertTableDoesNotExist(table)
