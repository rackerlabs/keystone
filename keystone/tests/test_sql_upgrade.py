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

1. Modify the file ``keystone/tests/backend_sql.conf`` to use the connection
   for your live database
2. Set up a blank, live database
3. Run the tests using::

    tox keystone.tests.test_sql_upgrade

WARNING::

    Your database will be wiped.

    Do not do this against a database with valuable data as all data will be
    lost.
"""

import json
import uuid

from migrate.versioning import api as versioning_api
import sqlalchemy

from keystone.assignment.backends import sql as assignment_sql
from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import config
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.db.sqlalchemy import session
from keystone import tests


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id
DB_INIT_VERSION = sql.DB_INIT_VERSION


class SqlMigrateBase(tests.TestCase):
    def initialize_sql(self):
        self.metadata = sqlalchemy.MetaData()
        self.metadata.bind = self.engine

    _config_file_list = [tests.dirs.etc('keystone.conf.sample'),
                         tests.dirs.tests('test_overrides.conf'),
                         tests.dirs.tests('backend_sql.conf')]

    #override this to specify the complete list of configuration files
    def config_files(self):
        return self._config_file_list

    def repo_package(self):
        return sql

    def _get_db_init_version(self):
        if self.repo_package() is not sql:
            return 0
        return DB_INIT_VERSION

    def _clean_up_db(self):
        sqlalchemy.orm.session.Session.close_all()
        for tbl in self.metadata.tables.keys():
            table = sqlalchemy.Table(tbl, self.metadata,
                                     autoload=True)
            table.drop(self.engine, checkfirst=True)
        session.cleanup()

    def setUp(self):
        super(SqlMigrateBase, self).setUp()

        self.config(self.config_files())

        db_init_version = self._get_db_init_version()
        self.addCleanup(self._clean_up_db)

        # create and share a single sqlalchemy engine for testing
        self.engine = session.get_engine()
        self.Session = session.get_maker(self.engine, autocommit=False)

        self.initialize_sql()
        self.repo_path = migration_helpers.find_migrate_repo(
            self.repo_package())
        self.schema = versioning_api.ControlledSchema.create(
            self.engine,
            self.repo_path, version=db_init_version)

        # auto-detect the highest available schema version in the migrate_repo
        self.max_version = self.schema.repository.version().version

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

    def downgrade(self, *args, **kwargs):
        self._migrate(*args, downgrade=True, **kwargs)

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
        self.assertEqual(expected_cols, actual_cols, '%s table' % table_name)


class SqlUpgradeTests(SqlMigrateBase):

    def test_blank_db_to_start(self):
        self.assertTableDoesNotExist('user')

    def test_start_version_at_DB_INIT_VERSION(self):
        version = migration.db_version(self.repo_path, DB_INIT_VERSION)
        self.assertEqual(version, DB_INIT_VERSION,
                         "DB is not at version %s" % DB_INIT_VERSION)

    def test_two_steps_forward_one_step_back(self):
        """You should be able to cleanly undo and re-apply all upgrades.

        Upgrades are run in the following order::

            0 -> 1 -> 0 -> 1 -> 2 -> 1 -> 2 -> 3 -> 2 -> 3 ...
                 ^---------^    ^---------^    ^---------^

        """
        # Since we cannot downgrate below version DB_INIT_VERSION -1 , make
        # sure we start with DB_INIT_VERSION +2 (minimum schema version we
        # can downgrade to is DB_INIT_VERSION +1 without error)
        first_walk_test_version = DB_INIT_VERSION + 2
        for x in range(first_walk_test_version, self.max_version + 1):
            self.upgrade(x)
            self.downgrade(x - 1)
            self.upgrade(x)

    def test_upgrade_add_initial_tables(self):
        self.upgrade(36)
        self.assertTableColumns('credential', ['id', 'user_id', 'project_id',
                                               'blob', 'type', 'extra'])
        self.assertTableColumns('domain', ['id', 'name', 'enabled', 'extra'])
        self.assertTableColumns('endpoint', ['id', 'legacy_endpoint_id',
                                             'interface', 'region',
                                             'service_id', 'url', 'extra'])
        self.assertTableColumns('group', ['id', 'domain_id', 'name',
                                          'description', 'extra'])
        self.assertTableColumns('group_domain_metadata', ['group_id',
                                                          'domain_id', 'data'])
        self.assertTableColumns('group_project_metadata', ['group_id',
                                                           'project_id',
                                                           'data'])
        self.assertTableColumns('policy', ['id', 'type', 'blob', 'extra'])
        self.assertTableColumns('project', ['id', 'name', 'extra',
                                            'description', 'enabled',
                                            'domain_id'])
        self.assertTableColumns('role', ['id', 'name', 'extra'])
        self.assertTableColumns('service', ['id', 'type', 'extra'])
        self.assertTableColumns('token', ['id', 'expires', 'extra', 'valid',
                                          'trust_id', 'user_id'])
        self.assertTableColumns('trust', ['id', 'trustor_user_id',
                                          'trustee_user_id', 'project_id',
                                          'impersonation', 'deleted_at',
                                          'expires_at', 'extra'])
        self.assertTableColumns('trust_role', ['trust_id', 'role_id'])
        self.assertTableColumns('user', ['id', 'name', 'extra', 'password',
                                         'enabled', 'domain_id',
                                         'default_project_id'])
        self.assertTableColumns('user_domain_metadata', ['user_id',
                                                         'domain_id', 'data'])
        self.assertTableColumns('user_group_membership', ['user_id',
                                                          'group_id'])
        self.assertTableColumns('user_project_metadata', ['user_id',
                                                          'project_id',
                                                          'data'])

    def insert_dict(self, session, table_name, d):
        """Naively inserts key-value pairs into a table, given a dictionary."""
        this_table = sqlalchemy.Table(table_name, self.metadata, autoload=True)
        insert = this_table.insert()
        insert.execute(d)
        session.commit()

    def test_downgrade_to_DB_INIT_VERSION(self):
        self.upgrade(self.max_version)

        if self.engine.name == 'mysql':
            self._mysql_check_all_tables_innodb()
        # Downgrade to the lowest supportable downgrade followed by
        # downgrade below supported version (pre-Havana)
        self.downgrade(DB_INIT_VERSION + 1)
        self.assertRaises(NotImplementedError, self.downgrade, DB_INIT_VERSION)

    def test_region_migration(self):
        self.upgrade(36)
        self.assertTableDoesNotExist('region')
        self.upgrade(37)
        self.assertTableExists('region')
        self.downgrade(36)
        self.assertTableDoesNotExist('region')

    def test_assignment_table_migration(self):

        def create_base_data(session):
            domain_table = sqlalchemy.Table('domain', self.metadata,
                                            autoload=True)
            user_table = sqlalchemy.Table('user', self.metadata, autoload=True)
            group_table = sqlalchemy.Table('group', self.metadata,
                                           autoload=True)
            role_table = sqlalchemy.Table('role', self.metadata, autoload=True)
            project_table = sqlalchemy.Table(
                'project', self.metadata, autoload=True)

            base_data = {}
            # Create a Domain
            base_data['domain'] = {'id': uuid.uuid4().hex,
                                   'name': uuid.uuid4().hex,
                                   'enabled': True}
            session.execute(domain_table.insert().values(base_data['domain']))

            # Create another Domain
            base_data['domain2'] = {'id': uuid.uuid4().hex,
                                    'name': uuid.uuid4().hex,
                                    'enabled': True}
            session.execute(domain_table.insert().values(base_data['domain2']))

            # Create a Project
            base_data['project'] = {'id': uuid.uuid4().hex,
                                    'name': uuid.uuid4().hex,
                                    'domain_id': base_data['domain']['id'],
                                    'extra': "{}"}
            session.execute(
                project_table.insert().values(base_data['project']))

            # Create another Project
            base_data['project2'] = {'id': uuid.uuid4().hex,
                                     'name': uuid.uuid4().hex,
                                     'domain_id': base_data['domain']['id'],
                                     'extra': "{}"}
            session.execute(
                project_table.insert().values(base_data['project2']))

            # Create a User
            base_data['user'] = {'id': uuid.uuid4().hex,
                                 'name': uuid.uuid4().hex,
                                 'domain_id': base_data['domain']['id'],
                                 'password': uuid.uuid4().hex,
                                 'enabled': True,
                                 'extra': "{}"}
            session.execute(user_table.insert().values(base_data['user']))

            # Create a Group
            base_data['group'] = {'id': uuid.uuid4().hex,
                                  'name': uuid.uuid4().hex,
                                  'domain_id': base_data['domain']['id'],
                                  'extra': "{}"}
            session.execute(group_table.insert().values(base_data['group']))

            # Create roles
            base_data['roles'] = []
            for _ in range(9):
                role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
                session.execute(role_table.insert().values(role))
                base_data['roles'].append(role)

            return base_data

        def populate_grants(session, base_data):

            user_project_table = sqlalchemy.Table(
                'user_project_metadata', self.metadata, autoload=True)
            user_domain_table = sqlalchemy.Table(
                'user_domain_metadata', self.metadata, autoload=True)
            group_project_table = sqlalchemy.Table(
                'group_project_metadata', self.metadata, autoload=True)
            group_domain_table = sqlalchemy.Table(
                'group_domain_metadata', self.metadata, autoload=True)

            # Grant a role to user on project
            grant = {'user_id': base_data['user']['id'],
                     'project_id': base_data['project']['id'],
                     'data': json.dumps(
                         {'roles': [{'id': base_data['roles'][0]['id']}]})}
            session.execute(user_project_table.insert().values(grant))

            # Grant two roles to user on project2
            grant = {'user_id': base_data['user']['id'],
                     'project_id': base_data['project2']['id'],
                     'data': json.dumps(
                         {'roles': [{'id': base_data['roles'][1]['id']},
                                    {'id': base_data['roles'][2]['id']}]})}
            session.execute(user_project_table.insert().values(grant))

            # Grant role to group on project
            grant = {'group_id': base_data['group']['id'],
                     'project_id': base_data['project']['id'],
                     'data': json.dumps(
                         {'roles': [{'id': base_data['roles'][3]['id']}]})}
            session.execute(group_project_table.insert().values(grant))

            # Grant two roles to group on project2
            grant = {'group_id': base_data['group']['id'],
                     'project_id': base_data['project2']['id'],
                     'data': json.dumps(
                         {'roles': [{'id': base_data['roles'][4]['id']},
                                    {'id': base_data['roles'][5]['id']}]})}
            session.execute(group_project_table.insert().values(grant))

            # Grant two roles to group on domain, one inherited, one not
            grant = {'group_id': base_data['group']['id'],
                     'domain_id': base_data['domain']['id'],
                     'data': json.dumps(
                         {'roles': [{'id': base_data['roles'][6]['id']},
                                    {'id': base_data['roles'][7]['id'],
                                     'inherited_to': 'projects'}]})}
            session.execute(group_domain_table.insert().values(grant))

            # Grant inherited role to user on domain
            grant = {'user_id': base_data['user']['id'],
                     'domain_id': base_data['domain']['id'],
                     'data': json.dumps(
                         {'roles': [{'id': base_data['roles'][8]['id'],
                                     'inherited_to': 'projects'}]})}
            session.execute(user_domain_table.insert().values(grant))

            # Grant two non-inherited roles to user on domain2, using roles
            # that are also assigned to other actors/targets
            grant = {'user_id': base_data['user']['id'],
                     'domain_id': base_data['domain2']['id'],
                     'data': json.dumps(
                         {'roles': [{'id': base_data['roles'][6]['id']},
                                    {'id': base_data['roles'][7]['id']}]})}
            session.execute(user_domain_table.insert().values(grant))

            session.commit()

        def check_grants(session, base_data):
            user_project_table = sqlalchemy.Table(
                'user_project_metadata', self.metadata, autoload=True)
            user_domain_table = sqlalchemy.Table(
                'user_domain_metadata', self.metadata, autoload=True)
            group_project_table = sqlalchemy.Table(
                'group_project_metadata', self.metadata, autoload=True)
            group_domain_table = sqlalchemy.Table(
                'group_domain_metadata', self.metadata, autoload=True)

            s = sqlalchemy.select([user_project_table.c.data]).where(
                (user_project_table.c.user_id == base_data['user']['id']) &
                (user_project_table.c.project_id ==
                 base_data['project']['id']))
            r = session.execute(s)
            data = json.loads(r.fetchone()['data'])
            self.assertEqual(len(data['roles']), 1)
            self.assertIn({'id': base_data['roles'][0]['id']}, data['roles'])

            s = sqlalchemy.select([user_project_table.c.data]).where(
                (user_project_table.c.user_id == base_data['user']['id']) &
                (user_project_table.c.project_id ==
                 base_data['project2']['id']))
            r = session.execute(s)
            data = json.loads(r.fetchone()['data'])
            self.assertEqual(len(data['roles']), 2)
            self.assertIn({'id': base_data['roles'][1]['id']}, data['roles'])
            self.assertIn({'id': base_data['roles'][2]['id']}, data['roles'])

            s = sqlalchemy.select([group_project_table.c.data]).where(
                (group_project_table.c.group_id == base_data['group']['id']) &
                (group_project_table.c.project_id ==
                 base_data['project']['id']))
            r = session.execute(s)
            data = json.loads(r.fetchone()['data'])
            self.assertEqual(len(data['roles']), 1)
            self.assertIn({'id': base_data['roles'][3]['id']}, data['roles'])

            s = sqlalchemy.select([group_project_table.c.data]).where(
                (group_project_table.c.group_id == base_data['group']['id']) &
                (group_project_table.c.project_id ==
                 base_data['project2']['id']))
            r = session.execute(s)
            data = json.loads(r.fetchone()['data'])
            self.assertEqual(len(data['roles']), 2)
            self.assertIn({'id': base_data['roles'][4]['id']}, data['roles'])
            self.assertIn({'id': base_data['roles'][5]['id']}, data['roles'])

            s = sqlalchemy.select([group_domain_table.c.data]).where(
                (group_domain_table.c.group_id == base_data['group']['id']) &
                (group_domain_table.c.domain_id == base_data['domain']['id']))
            r = session.execute(s)
            data = json.loads(r.fetchone()['data'])
            self.assertEqual(len(data['roles']), 2)
            self.assertIn({'id': base_data['roles'][6]['id']}, data['roles'])
            self.assertIn({'id': base_data['roles'][7]['id'],
                           'inherited_to': 'projects'}, data['roles'])

            s = sqlalchemy.select([user_domain_table.c.data]).where(
                (user_domain_table.c.user_id == base_data['user']['id']) &
                (user_domain_table.c.domain_id == base_data['domain']['id']))
            r = session.execute(s)
            data = json.loads(r.fetchone()['data'])
            self.assertEqual(len(data['roles']), 1)
            self.assertIn({'id': base_data['roles'][8]['id'],
                           'inherited_to': 'projects'}, data['roles'])

            s = sqlalchemy.select([user_domain_table.c.data]).where(
                (user_domain_table.c.user_id == base_data['user']['id']) &
                (user_domain_table.c.domain_id == base_data['domain2']['id']))
            r = session.execute(s)
            data = json.loads(r.fetchone()['data'])
            self.assertEqual(len(data['roles']), 2)
            self.assertIn({'id': base_data['roles'][6]['id']}, data['roles'])
            self.assertIn({'id': base_data['roles'][7]['id']}, data['roles'])

        def check_assignments(session, base_data):

            def check_assignment_type(refs, type):
                for ref in refs:
                    self.assertEqual(ref.type, type)

            assignment_table = sqlalchemy.Table(
                'assignment', self.metadata, autoload=True)

            refs = session.query(assignment_table).all()
            self.assertEqual(len(refs), 11)

            q = session.query(assignment_table)
            q = q.filter_by(actor_id=base_data['user']['id'])
            q = q.filter_by(target_id=base_data['project']['id'])
            refs = q.all()
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].role_id, base_data['roles'][0]['id'])
            self.assertFalse(refs[0].inherited)
            check_assignment_type(refs,
                                  assignment_sql.AssignmentType.USER_PROJECT)

            q = session.query(assignment_table)
            q = q.filter_by(actor_id=base_data['user']['id'])
            q = q.filter_by(target_id=base_data['project2']['id'])
            refs = q.all()
            self.assertEqual(len(refs), 2)
            role_ids = [base_data['roles'][1]['id'],
                        base_data['roles'][2]['id']]
            self.assertIn(refs[0].role_id, role_ids)
            self.assertIn(refs[1].role_id, role_ids)
            self.assertFalse(refs[0].inherited)
            self.assertFalse(refs[1].inherited)
            check_assignment_type(refs,
                                  assignment_sql.AssignmentType.USER_PROJECT)

            q = session.query(assignment_table)
            q = q.filter_by(actor_id=base_data['group']['id'])
            q = q.filter_by(target_id=base_data['project']['id'])
            refs = q.all()
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].role_id, base_data['roles'][3]['id'])
            self.assertFalse(refs[0].inherited)
            check_assignment_type(refs,
                                  assignment_sql.AssignmentType.GROUP_PROJECT)

            q = session.query(assignment_table)
            q = q.filter_by(actor_id=base_data['group']['id'])
            q = q.filter_by(target_id=base_data['project2']['id'])
            refs = q.all()
            self.assertEqual(len(refs), 2)
            role_ids = [base_data['roles'][4]['id'],
                        base_data['roles'][5]['id']]
            self.assertIn(refs[0].role_id, role_ids)
            self.assertIn(refs[1].role_id, role_ids)
            self.assertFalse(refs[0].inherited)
            self.assertFalse(refs[1].inherited)
            check_assignment_type(refs,
                                  assignment_sql.AssignmentType.GROUP_PROJECT)

            q = session.query(assignment_table)
            q = q.filter_by(actor_id=base_data['group']['id'])
            q = q.filter_by(target_id=base_data['domain']['id'])
            refs = q.all()
            self.assertEqual(len(refs), 2)
            role_ids = [base_data['roles'][6]['id'],
                        base_data['roles'][7]['id']]
            self.assertIn(refs[0].role_id, role_ids)
            self.assertIn(refs[1].role_id, role_ids)
            if refs[0].role_id == base_data['roles'][7]['id']:
                self.assertTrue(refs[0].inherited)
                self.assertFalse(refs[1].inherited)
            else:
                self.assertTrue(refs[1].inherited)
                self.assertFalse(refs[0].inherited)
            check_assignment_type(refs,
                                  assignment_sql.AssignmentType.GROUP_DOMAIN)

            q = session.query(assignment_table)
            q = q.filter_by(actor_id=base_data['user']['id'])
            q = q.filter_by(target_id=base_data['domain']['id'])
            refs = q.all()
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].role_id, base_data['roles'][8]['id'])
            self.assertTrue(refs[0].inherited)
            check_assignment_type(refs,
                                  assignment_sql.AssignmentType.USER_DOMAIN)

            q = session.query(assignment_table)
            q = q.filter_by(actor_id=base_data['user']['id'])
            q = q.filter_by(target_id=base_data['domain2']['id'])
            refs = q.all()
            self.assertEqual(len(refs), 2)
            role_ids = [base_data['roles'][6]['id'],
                        base_data['roles'][7]['id']]
            self.assertIn(refs[0].role_id, role_ids)
            self.assertIn(refs[1].role_id, role_ids)
            self.assertFalse(refs[0].inherited)
            self.assertFalse(refs[1].inherited)
            check_assignment_type(refs,
                                  assignment_sql.AssignmentType.USER_DOMAIN)

        self.upgrade(37)
        session = self.Session()
        self.assertTableDoesNotExist('assignment')
        base_data = create_base_data(session)
        populate_grants(session, base_data)
        check_grants(session, base_data)
        session.commit()
        session.close()
        self.upgrade(40)
        session = self.Session()
        self.assertTableExists('assignment')
        self.assertTableDoesNotExist('user_project_metadata')
        self.assertTableDoesNotExist('group_project_metadata')
        self.assertTableDoesNotExist('user_domain_metadata')
        self.assertTableDoesNotExist('group_domain_metadata')
        check_assignments(session, base_data)
        session.close()
        self.downgrade(37)
        session = self.Session()
        self.assertTableDoesNotExist('assignment')
        check_grants(session, base_data)
        session.close()

    def test_limited_trusts_upgrade(self):
        # make sure that the remaining_uses column is created
        self.upgrade(41)
        self.assertTableColumns('trust',
                                ['id', 'trustor_user_id',
                                 'trustee_user_id',
                                 'project_id', 'impersonation',
                                 'deleted_at',
                                 'expires_at', 'extra',
                                 'remaining_uses'])

    def test_limited_trusts_downgrade(self):
        # make sure that the remaining_uses column is removed
        self.upgrade(41)
        self.downgrade(40)
        self.assertTableColumns('trust',
                                ['id', 'trustor_user_id',
                                 'trustee_user_id',
                                 'project_id', 'impersonation',
                                 'deleted_at',
                                 'expires_at', 'extra'])

    def test_limited_trusts_downgrade_trusts_cleanup(self):
        # make sure that only trusts with unlimited uses are kept in the
        # downgrade
        self.upgrade(41)
        session = self.Session()
        trust_table = sqlalchemy.Table(
            'trust', self.metadata, autoload=True)
        limited_trust = {
            'id': uuid.uuid4().hex,
            'trustor_user_id': uuid.uuid4().hex,
            'trustee_user_id': uuid.uuid4().hex,
            'project_id': uuid.uuid4().hex,
            'impersonation': True,
            'remaining_uses': 5
        }
        consumed_trust = {
            'id': uuid.uuid4().hex,
            'trustor_user_id': uuid.uuid4().hex,
            'trustee_user_id': uuid.uuid4().hex,
            'project_id': uuid.uuid4().hex,
            'impersonation': True,
            'remaining_uses': 0
        }
        unlimited_trust = {
            'id': uuid.uuid4().hex,
            'trustor_user_id': uuid.uuid4().hex,
            'trustee_user_id': uuid.uuid4().hex,
            'project_id': uuid.uuid4().hex,
            'impersonation': True,
            'remaining_uses': None
        }
        self.insert_dict(session, 'trust', limited_trust)
        self.insert_dict(session, 'trust', consumed_trust)
        self.insert_dict(session, 'trust', unlimited_trust)
        trust_table = sqlalchemy.Table(
            'trust', self.metadata, autoload=True)
        # we should have 3 trusts in base
        self.assertEqual(3, session.query(trust_table).count())

        self.downgrade(40)
        session = self.Session()
        trust_table = sqlalchemy.Table(
            'trust', self.metadata, autoload=True)
        # Now only one trust remains ...
        self.assertEqual(1, session.query(trust_table.columns.id).count())
        # ... and this trust is the one that was not limited in uses
        self.assertEqual(
            unlimited_trust['id'],
            session.query(trust_table.columns.id).one()[0])

    def _mysql_check_all_tables_innodb(self):
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
        self.assertEqual(names, [],
                         "Non-InnoDB tables exist")

        connection.close()
