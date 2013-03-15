# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 IBM
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Tests for database migrations. This test case reads the configuration
file test_migrations.conf for database connection settings
to use in the tests. For each connection found in the config file,
the test case runs a series of test cases to ensure that migrations work
properly both upgrading and downgrading, and that no data loss occurs
if possible.
"""

import commands
import ConfigParser
import datetime
import json
import os
import urlparse
import uuid

from migrate.versioning import repository
import sqlalchemy

from keystone.common.sql import migration
import keystone.common.sql.migrate_repo
from keystone.common.sql.migration import versioning_api as migration_api
from keystone.common import logging
from keystone import config
from keystone import test

CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id
LOG = logging.getLogger('keystone.tests.test_migrations')


def _get_connect_string(backend,
                        user="openstack_citest",
                        passwd="openstack_citest",
                        database="openstack_citest"):
    """
    Try to get a connection with a very specific set of values, if we get
    these then we'll run the tests, otherwise they are skipped
    """
    if backend == "postgres":
        backend = "postgresql+psycopg2"

    return ("%(backend)s://%(user)s:%(passwd)s@localhost/%(database)s"
            % locals())


def _is_mysql_avail(**kwargs):
    return _is_backend_avail('mysql', **kwargs)


def _is_backend_avail(backend,
                      user="openstack_citest",
                      passwd="openstack_citest",
                      database="openstack_citest"):
    try:
        if backend == "mysql":
            connect_uri = _get_connect_string("mysql", user=user,
                                              passwd=passwd, database=database)
        elif backend == "postgres":
            connect_uri = _get_connect_string("postgres", user=user,
                                              passwd=passwd, database=database)
        engine = sqlalchemy.create_engine(connect_uri)
        connection = engine.connect()
    except Exception as exc:
        # intentionally catch all to handle exceptions even if we don't
        # have any backend code loaded.
        return False
    else:
        connection.close()
        engine.dispose()
        return True


def _have_mysql():
    present = os.environ.get('NOVA_TEST_MYSQL_PRESENT')
    if present is None:
        return _is_backend_avail('mysql')
    return present.lower() in ('', 'true')


def get_table(engine, name):
    """Returns an sqlalchemy table dynamically from db.

    Needed because the models don't work for us in migrations
    as models will be far out of sync with the current data."""
    metadata = sqlalchemy.schema.MetaData()
    metadata.bind = engine
    return sqlalchemy.Table(name, metadata, autoload=True)


class TestMigrations(test.TestCase):
    """Test sqlalchemy-migrate migrations."""

    DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                                       'test_migrations.conf')
    # Test machines can set the KEYSTONE_TEST_MIGRATIONS_CONF variable
    # to override the location of the config file for migration testing
    CONFIG_FILE_PATH = os.environ.get('KEYSTONE_TEST_MIGRATIONS_CONF',
                                      DEFAULT_CONFIG_FILE)
    MIGRATE_FILE = keystone.common.sql.migrate_repo.__file__
    REPOSITORY = repository.Repository(
        os.path.abspath(os.path.dirname(MIGRATE_FILE)))

    def setUp(self):
        super(TestMigrations, self).setUp()

        self.snake_walk = False
        self.test_databases = {}

        # Load test databases from the config file. Only do this
        # once. No need to re-run this on each test...
        LOG.debug('config_path is %s' % TestMigrations.CONFIG_FILE_PATH)
        if not self.test_databases:
            if os.path.exists(TestMigrations.CONFIG_FILE_PATH):
                cp = ConfigParser.RawConfigParser()
                try:
                    cp.read(TestMigrations.CONFIG_FILE_PATH)
                    defaults = cp.defaults()
                    for key, value in defaults.items():
                        self.test_databases[key] = value
                    self.snake_walk = cp.getboolean('walk_style', 'snake_walk')
                except ConfigParser.ParsingError, e:
                    self.fail("Failed to read test_migrations.conf config "
                              "file. Got error: %s" % e)
            else:
                self.fail("Failed to find test_migrations.conf config "
                          "file.")

        self.engines = {}
        for key, value in self.test_databases.items():
            self.engines[key] = sqlalchemy.create_engine(value)

        # We start each test case with a completely blank slate.
        self._reset_databases()

    def tearDown(self):

        # We destroy the test data store between each test case,
        # and recreate it, which ensures that we have no side-effects
        # from the tests
        self._reset_databases()
        super(TestMigrations, self).tearDown()

    def _reset_databases(self):
        def execute_cmd(cmd=None):
            status, output = commands.getstatusoutput(cmd)
            LOG.debug(output)
            self.assertEqual(0, status)
        for key, engine in self.engines.items():
            conn_string = self.test_databases[key]
            conn_pieces = urlparse.urlparse(conn_string)
            engine.dispose()
            if conn_string.startswith('sqlite'):
                # We can just delete the SQLite database, which is
                # the easiest and cleanest solution
                db_path = conn_pieces.path.strip('/')
                if os.path.exists(db_path):
                    os.unlink(db_path)
                # No need to recreate the SQLite DB. SQLite will
                # create it for us if it's not there...
            elif conn_string.startswith('mysql'):
                # We can execute the MySQL client to destroy and re-create
                # the MYSQL database, which is easier and less error-prone
                # than using SQLAlchemy to do this via MetaData...trust me.
                database = conn_pieces.path.strip('/')
                loc_pieces = conn_pieces.netloc.split('@')
                host = loc_pieces[1]
                auth_pieces = loc_pieces[0].split(':')
                user = auth_pieces[0]
                password = ""
                if len(auth_pieces) > 1:
                    if auth_pieces[1].strip():
                        password = "-p\"%s\"" % auth_pieces[1]
                sql = ("drop database if exists %(database)s; "
                       "create database %(database)s;") % locals()
                cmd = ("mysql -u \"%(user)s\" %(password)s -h %(host)s "
                       "-e \"%(sql)s\"") % locals()
                execute_cmd(cmd)
            elif conn_string.startswith('postgresql'):
                database = conn_pieces.path.strip('/')
                loc_pieces = conn_pieces.netloc.split('@')
                host = loc_pieces[1]

                auth_pieces = loc_pieces[0].split(':')
                user = auth_pieces[0]
                password = ""
                if len(auth_pieces) > 1:
                    password = auth_pieces[1].strip()
                # note(krtaylor): File creation problems with tests in
                # venv using .pgpass authentication, changed to
                # PGPASSWORD environment variable which is no longer
                # planned to be deprecated
                os.environ['PGPASSWORD'] = password
                os.environ['PGUSER'] = user
                # note(boris-42): We must create and drop database, we can't
                # drop database which we have connected to, so for such
                # operations there is a special database template1.
                sqlcmd = ("psql -w -U %(user)s -h %(host)s -c"
                          " '%(sql)s' -d template1")
                sql = ("drop database if exists %(database)s;") % locals()
                droptable = sqlcmd % locals()
                execute_cmd(droptable)
                sql = ("create database %(database)s;") % locals()
                createtable = sqlcmd % locals()
                execute_cmd(createtable)
                os.unsetenv('PGPASSWORD')
                os.unsetenv('PGUSER')

    def test_walk_versions(self):
        """
        Walks all version scripts for each tested database, ensuring
        that there are no errors in the version scripts for each engine
        """
        for key, engine in self.engines.items():
            self._walk_versions(engine, self.snake_walk)

    def test_mysql_connect_fail(self):
        """
        Test that we can trigger a mysql connection failure and we fail
        gracefully to ensure we don't break people without mysql
        """
        if _is_mysql_avail(user="openstack_cifail"):
            self.fail("Shouldn't have connected")

    @test.skip_unless(_have_mysql(), "mysql not available")
    def test_mysql_opportunistically(self):
        # add this to the global lists to make reset work with it, it's removed
        # automaticaly in tearDown so no need to clean it up here.
        connect_string = _get_connect_string('mysql')
        engine = sqlalchemy.create_engine(connect_string)
        self.engines["mysqlcitest"] = engine
        self.test_databases["mysqlcitest"] = connect_string

        # build a fully populated mysql database with all the tables
        self._reset_databases()
        self._walk_versions(engine, False, False)

    def test_postgresql_connect_fail(self):
        """
        Test that we can trigger a postgres connection failure and we fail
        gracefully to ensure we don't break people without postgres
        """
        if _is_backend_avail('postgres', user="openstack_cifail"):
            self.fail("Shouldn't have connected")

    @test.skip_unless(_is_backend_avail('postgres'),
                      "postgresql not available")
    def test_postgresql_opportunistically(self):
        # add this to the global lists to make reset work with it, it's removed
        # automatically in tearDown so no need to clean it up here.
        connect_string = _get_connect_string("postgres")
        engine = sqlalchemy.create_engine(connect_string)
        self.engines["postgresqlcitest"] = engine
        self.test_databases["postgresqlcitest"] = connect_string

        # build a fully populated postgresql database with all the tables
        self._reset_databases()
        self._walk_versions(engine, False, False)

    def _walk_versions(self, engine=None, snake_walk=False, downgrade=True):
        # Determine latest version script from the repo, then
        # upgrade from 1 through to the latest, with no data
        # in the databases. This just checks that the schema itself
        # upgrades successfully.

        # Place the database under version control
        migration_api.version_control(engine,
                                      TestMigrations.REPOSITORY,
                                      migration.INIT_VERSION)
        self.assertEqual(migration.INIT_VERSION,
                         migration_api.db_version(engine,
                                                  TestMigrations.REPOSITORY))

        migration_api.upgrade(engine, TestMigrations.REPOSITORY,
                              migration.INIT_VERSION + 1)

        LOG.debug('latest version is %s' % TestMigrations.REPOSITORY.latest)

        for version in xrange(migration.INIT_VERSION + 2,
                              TestMigrations.REPOSITORY.latest + 1):
            # upgrade -> downgrade -> upgrade
            self._migrate_up(engine, version, with_data=True)
            if snake_walk:
                self._migrate_down(engine, version - 1)
                self._migrate_up(engine, version)

        if downgrade:
            # Now walk it back down to 0 from the latest, testing
            # the downgrade paths.
            for version in reversed(
                xrange(migration.INIT_VERSION + 1,
                       TestMigrations.REPOSITORY.latest)):
                # downgrade -> upgrade -> downgrade
                self._migrate_down(engine, version)
                if snake_walk:
                    self._migrate_up(engine, version + 1)
                    self._migrate_down(engine, version)

    def _migrate_down(self, engine, version):
        migration_api.downgrade(engine,
                                TestMigrations.REPOSITORY,
                                version)
        self.assertEqual(version,
                         migration_api.db_version(engine,
                                                  TestMigrations.REPOSITORY))

    def _migrate_up(self, engine, version, with_data=False):
        """migrate up to a new version of the db.

        We allow for data insertion and post checks at every
        migration version with special _prerun_### and
        _check_### functions in the main test.
        """
        # NOTE(sdague): try block is here because it's impossible to debug
        # where a failed data migration happens otherwise
        try:
            if with_data:
                data = None
                prerun = getattr(self, "_prerun_%3.3d" % version, None)
                if prerun:
                    data = prerun(engine)

            migration_api.upgrade(engine,
                                  TestMigrations.REPOSITORY,
                                  version)
            self.assertEqual(
                version,
                migration_api.db_version(engine,
                                         TestMigrations.REPOSITORY))

            if with_data:
                check = getattr(self, "_check_%3.3d" % version, None)
                if check:
                    check(engine, data)
        except Exception:
            LOG.error("Failed to migrate to version %s on engine %s" %
                      (version, engine))
            raise

    # migration 002 - adds token_id_hash
    def _prerun_002(self, engine):
        data = [{'id': str(uuid.uuid4()),
                 'expires': datetime.datetime(2013, 1, 1, 0, 0, 0),
                 'extra': 'ExtraInfo1'},
                {'id': str(uuid.uuid4()),
                 'expires': datetime.datetime(2014, 2, 3, 1, 2, 3),
                 'extra': 'ExtraInfo2'},
                {'id': str(uuid.uuid4()),
                 'expires': datetime.datetime(2015, 4, 5, 6, 7, 8),
                 'extra': 'ExtraInfo3'}
                ]

        tokens = get_table(engine, 'token')
        engine.execute(tokens.insert(), data)
        return data

    def _check_002(self, engine, data):
        tokens = get_table(engine, 'token')

        # Check the new column was created
        self.assertIn('id_hash', tokens.c)

        # Check if all rows have been inserted
        token_items = tokens.select().execute().fetchall()
        self.assertEqual(len(token_items), len(data))

        # Check data has migrated correctly
        for data_row in data:
            row = tokens.select(
                tokens.c.id_hash == data_row['id']).execute().first()
            # The SQLite version adds '' instead of None in the
            # upgrade path for the new column but perhaps it shouldn't
            # to be consistent with MySQL and PostgreSQL?
            self.assertIn(row['id'], (None, ''))
            self.assertEqual(row['expires'], data_row['expires'])
            self.assertEqual(row['extra'], data_row['extra'])

    # migration 004 - reverts token_id_hash
    def _prerun_004(self, engine):
        data = [{'id_hash': str(uuid.uuid4()),
                 'id': "ID1",
                 'valid': True,
                 'expires': datetime.datetime(2013, 1, 1, 0, 0, 0),
                 'extra': 'ExtraInfo1'},
                {'id_hash': str(uuid.uuid4()),
                 'id': "ID2",
                 'valid': True,
                 'expires': datetime.datetime(2014, 2, 3, 1, 2, 3),
                 'extra': 'ExtraInfo2'},
                {'id_hash': str(uuid.uuid4()),
                 'id': "ID3",
                 'valid': True,
                 'expires': datetime.datetime(2015, 4, 5, 6, 7, 8),
                 'extra': 'ExtraInfo3'}
                ]

        tokens = get_table(engine, 'token')
        engine.execute(tokens.insert(), data)
        return data

    def _check_004(self, engine, data):
        tokens = get_table(engine, 'token')

        # Check the id_hash column no longer exists
        self.assertNotIn('id_hash', tokens.c)

        # Check data has migrated correctly
        for data_row in data:
            row = tokens.select(tokens.c.id == data_row['id_hash']).execute().\
                first()
            self.assertEqual(row['expires'], data_row['expires'])
            self.assertEqual(row['extra'], data_row['extra'])
            self.assertEqual(row['valid'], data_row['valid'])

    def _prerun_007(self, engine):
        data = [{'id': str(uuid.uuid4()),
                 'name': 'Test Role 1'},
                {'id': str(uuid.uuid4()),
                 'name': 'Test Role 2'}
                ]
        roles = get_table(engine, 'role')
        engine.execute(roles.insert(), data)
        return data

    def _check_007(self, engine, data):
        roles = get_table(engine, 'role')

        self.assertIn('extra', roles.c)
        for data_row in data:
            row = roles.select(roles.c.id == data_row['id']).execute().first()
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['extra'], None)
            # extra should really be '{}' and is fixed up in migration 019

    data_009 = {
        'user': [{'id': str(uuid.uuid4()),
                  'name': 'Name 1',
                  'extra': '{"password": "foo", "enabled": true}'},
                 {'id': str(uuid.uuid4()),
                  'name': 'Name 2',
                  'extra': '{"password": "bar", "enabled": false}'},
                 {'id': str(uuid.uuid4()),
                  'name': 'Name 3',
                  'extra': '{"password": "baz", "enabled": true}'},
                 ],
        'tenant': [{'id': str(uuid.uuid4()),
                    'name': 'Tenant Name 1',
                    'extra': '{"description": "Desc1", "enabled": false}'},
                   {'id': str(uuid.uuid4()),
                    'name': 'Tenant Name 2',
                    'extra': '{"description": "Desc2", "enabled": true}'},
                   ]}

    # migration 009 - normalise identity tables
    #  this stage just adds the new columns
    def _prerun_009(self, engine):
        users = get_table(engine, 'user')
        engine.execute(users.insert(), self.data_009['user'])
        tenants = get_table(engine, 'tenant')
        engine.execute(tenants.insert(), self.data_009['tenant'])
        return self.data_009

    def _check_009(self, engine, data):

        # Check columns have been added correctly
        users = get_table(engine, 'user')
        self.assertIn('password', users.c)
        self.assertIn('enabled', users.c)

        tenants = get_table(engine, 'tenant')
        self.assertIn('description', tenants.c)
        self.assertIn('enabled', tenants.c)

        # Check data has migrated correctly
        for data_row in data['user']:
            row = users.select(
                users.c.id == data_row['id']).execute().first()
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['extra'], data_row['extra'])

        for data_row in data['tenant']:
            row = tenants.select(
                tenants.c.id == data_row['id']).execute().first()
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['extra'], data_row['extra'])

    def _check_010(self, engine, data):
        # Data used to test 010 migration was injected in 009
        users = get_table(engine, 'user')
        for data_row in self.data_009['user']:
            row = users.select(
                users.c.id == data_row['id']).execute().first()
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['extra'], '{}')
            extra = json.loads(data_row['extra'])
            self.assertEqual(row['password'], extra['password'])
            self.assertEqual(row['enabled'], extra['enabled'])

        tenants = get_table(engine, 'tenant')
        for data_row in self.data_009['tenant']:
            row = tenants.select(
                tenants.c.id == data_row['id']).execute().first()
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['extra'], '{}')
            extra = json.loads(data_row['extra'])
            self.assertEqual(row['description'], extra['description'])
            self.assertEqual(row['enabled'], extra['enabled'])

    data_011 = {
        'service': [{'id': 'e78732f29b1140ecbd969fbd9212fa27',
                     'type': '23ce4c88438843de9bde87c3f13db1fd',
                     'extra': '{"name": "Foo Service"'},
                    {'id': '287a6f72b75f4cc7b5e54803585ce096',
                     'type': '79efb5833f2245409316e7725edff65e',
                     'extra': '{"name": "Bar Service"'},
                    ],
        'endpoint': [
            {'id': '801fde29ecbb4020a90c7e94d88982ed',
             'region': 'a78a45188ac34e7da45e3175b1e4c433',
             'service_id': 'e78732f29b1140ecbd969fbd9212fa27',
             'extra': '{"publicurl": "9cfc5ede0b824c0fbc92e8f4cf98a972",'
                       '"internalurl": "b4c1be81664a4e028f85af12a3422625",'
                       '"adminurl": "c4ee91dbe23043e593b0f1a75d78a59d"}'},
            {'id': '90c7e516f7c64b6fbf3df57c9e99ea3a',
             'region': 'e7904d5090af4b159c5200e07f6336e1',
             'service_id': 'e78732f29b1140ecbd969fbd9212fa27',
             'extra': '{"publicurl": "34f1dd31eba4470f9f9603e529b13e9c",'
                       '"internalurl": "fa48caeec95c4cd6bdc4fec1a09cf038",'
                       '"adminurl": "e9e94b2fdf6241c488e8460e724ad2e9"}'},
        ]}

    # migration 011 - normalise identity tables
    #  this stage just adds the new columns
    def _prerun_011(self, engine):
        services = get_table(engine, 'service')
        engine.execute(services.insert(), self.data_011['service'])
        endpoints = get_table(engine, 'endpoint')
        engine.execute(endpoints.insert(), self.data_011['endpoint'])

        return self.data_011

    def _check_011(self, engine, data):
        endpoint_v2 = get_table(engine, 'endpoint_v2')
        endpoint_v3 = get_table(engine, 'endpoint_v3')

        # Check columns have been added correctly
        self.assertIn('id', endpoint_v3.c)
        self.assertIn('legacy_endpoint_id', endpoint_v3.c)
        self.assertIn('interface', endpoint_v3.c)
        self.assertIn('region', endpoint_v3.c)
        self.assertIn('service_id', endpoint_v3.c)
        self.assertIn('url', endpoint_v3.c)
        self.assertIn('extra', endpoint_v3.c)

    def _check_012(self, engine, data):
        # Data for 012 test was injected in 011

        # Check the migration of the data from the endpoint_v2
        # to endpoint_v3 table occurred correctly
        endpoints = get_table(engine, 'endpoint_v3')
        endpoint_rows = endpoints.select().execute().fetchall()

        for endpoint_row in endpoint_rows:
            data_row = [ep for ep in self.data_011['endpoint']
                        if ep['id'] == endpoint_row['legacy_endpoint_id']]
            self.assertEqual(data_row[0]['region'], endpoint_row['region'])
            extra = json.loads(data_row[0]['extra'])
            self.assertIn('%surl' % endpoint_row['interface'], extra.keys())
            self.assertEqual(endpoint_row['extra'], '{}')
            self.assertEqual(data_row[0]['service_id'],
                             endpoint_row['service_id'])

    def _check_013(self, engine, data):
        # Data for 013 test was injected in 011

        # Check the migration of the data occurred correctly to the
        # endpoint table
        endpoints = get_table(engine, 'endpoint')
        endpoint_rows = endpoints.select().execute().fetchall()

        for endpoint_row in endpoint_rows:
            data_row = [ep for ep in self.data_011['endpoint']
                        if ep['id'] == endpoint_row['legacy_endpoint_id']]
            self.assertEqual(data_row[0]['region'], endpoint_row['region'])
            extra = json.loads(data_row[0]['extra'])
            self.assertIn('%surl' % endpoint_row['interface'], extra.keys())
            self.assertEqual(endpoint_row['extra'], '{}')
            self.assertEqual(data_row[0]['service_id'],
                             endpoint_row['service_id'])

        # Confirm the endpoint_v2 table no longer exists
        self.assertRaises(sqlalchemy.exc.NoSuchTableError,
                          get_table, engine, 'endpoint_v2')

    data_015 = {
        'user_tenant_membership':
        [{'user_id': data_009['user'][0]['id'],
          'tenant_id': data_009['tenant'][0]['id']},
         {'user_id': data_009['user'][1]['id'],
          'tenant_id': data_009['tenant'][1]['id']},
         ],
        'tenant': []}

    def _prerun_015(self, engine):
        user_tenant_memberships = get_table(engine, 'user_tenant_membership')
        engine.execute(user_tenant_memberships.insert(),
                       self.data_015['user_tenant_membership'])

        # Use existing tenant data originally injected in 009, but we
        # have to retrieve a copy of it because in 010 it was
        # transformed and so can not reference in the data_009 as it does
        # not in a convenient layout.
        tenants = get_table(engine, 'tenant')
        tenant_items = tenants.select().execute().fetchall()
        for tenant_row in tenant_items:
            self.data_015['tenant'].append(
                {'id': tenant_row['id'],
                 'name': tenant_row['name'],
                 'description': tenant_row['description'],
                 'enabled': tenant_row['enabled'],
                 'extra': tenant_row['extra']})

    def _check_015(self, engine, data):
        # Check data was copied correctly
        user_project_memberships = get_table(engine, 'user_project_membership')
        for data_row in self.data_015['user_tenant_membership']:
            row = user_project_memberships.select(
                user_project_memberships.c.user_id ==
                data_row['user_id']).execute().first()
            self.assertEqual(row['tenant_id'], data_row['tenant_id'])

        projects = get_table(engine, 'project')
        for data_row in self.data_015['tenant']:
            row = projects.select(
                projects.c.id == data_row['id']).execute().first()
            self.assertEqual(row['id'], data_row['id'])
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['extra'], data_row['extra'])
            self.assertEqual(row['description'], data_row['description'])

        # Ensure old tables no longer exist
        self.assertRaises(sqlalchemy.exc.NoSuchTableError,
                          get_table, engine, 'tenants')
        self.assertRaises(sqlalchemy.exc.NoSuchTableError,
                          get_table, engine, 'user_tenant_membership')

    data_016 = {'user': []}

    def _prerun_016(self, engine):
        # Use existing user data originally injected in 009, but we
        # have to retrieve a copy of it because in 010 it was
        # transformed and so can not reference in the data_009 as it does
        # not in a convenient layout.
        users = get_table(engine, 'user')
        user_items = users.select().execute().fetchall()
        for user_row in user_items:
            self.data_016['user'].append(
                {'id': user_row['id'],
                 'name': user_row['name'],
                 'password': user_row['password'],
                 'enabled': user_row['enabled'],
                 'extra': user_row['extra']})

    # Reuse the tenant table created for migration 015
    def _check_016(self, engine, data):
        users = get_table(engine, 'user')
        for data_row in self.data_016['user']:
            row = users.select(
                users.c.id == data_row['id']).execute().first()
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['password'], data_row['password'])
            self.assertEqual(row['enabled'], data_row['enabled'])
            self.assertEqual(row['extra'], data_row['extra'])
            self.assertEqual(row['domain_id'], DEFAULT_DOMAIN_ID)

        projects = get_table(engine, 'project')
        for data_row in self.data_015['tenant']:
            row = projects.select(
                projects.c.id == data_row['id']).execute().first()
            self.assertEqual(row['name'], data_row['name'])
            self.assertEqual(row['description'], data_row['description'])
            self.assertEqual(row['enabled'], data_row['enabled'])
            self.assertEqual(row['extra'], data_row['extra'])
            self.assertEqual(row['domain_id'], DEFAULT_DOMAIN_ID)

    def _prerun_017(self, engine):
        user_project_memberships = get_table(engine, 'user_project_membership')
        upm_rows = user_project_memberships.select().execute().fetchall()

        data = []
        for upm_row in upm_rows:
            data.append({'user_id': upm_row.user_id,
                         'tenant_id': upm_row.tenant_id})

        return data

    def _check_017(self, engine, data):
        roles = get_table(engine, 'role')
        default_role = roles.select(
            roles.c.id == CONF.member_role_id).execute().first()
        self.assertEqual(default_role['name'], CONF.member_role_name)

        up_meta = get_table(engine, 'user_project_metadata')
        for data_row in data:
            row = up_meta.select(
                up_meta.c.user_id == data_row['user_id']).execute().first()
            self.assertEqual(row['project_id'], data_row['tenant_id'])
            self.assertEqual(
                row['data'],
                json.dumps({'roles': [config.CONF.member_role_id]}))

        self.assertRaises(sqlalchemy.exc.NoSuchTableError,
                          get_table, engine, 'user_project_membership')

    def _check_019(self, engine, data):
        # Use the role data injected in the 007 migration test
        roles = get_table(engine, 'role')
        role_items = roles.select().execute().fetchall()

        # verify that all of the extra fields have been fixed
        for role_row in role_items:
            self.assertNotEqual(role_row['extra'], None)
