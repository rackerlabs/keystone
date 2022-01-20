# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Tests for database migrations for the database.

These are "opportunistic" tests which allow testing against all three databases
(sqlite in memory, mysql, pg) in a properly configured unit test environment.

For the opportunistic testing you need to set up DBs named 'openstack_citest'
with user 'openstack_citest' and password 'openstack_citest' on localhost. The
test will then use that DB and username/password combo to run the tests.
"""

import os

from alembic import command as alembic_api
from alembic import script as alembic_script
import fixtures
from migrate.versioning import api as migrate_api
from oslo_db import options as db_options
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures
from oslo_db.sqlalchemy import test_migrations
from oslo_log.fixture import logging_error as log_fixture
from oslo_log import log as logging
from oslotest import base

from keystone.common import sql
from keystone.common.sql import upgrades
import keystone.conf
from keystone.tests import unit
from keystone.tests.unit import ksfixtures

# We need to import all of these so the tables are registered. It would be
# easier if these were all in a central location :(
import keystone.application_credential.backends.sql  # noqa: F401
import keystone.assignment.backends.sql  # noqa: F401
import keystone.assignment.role_backends.sql_model  # noqa: F401
import keystone.catalog.backends.sql  # noqa: F401
import keystone.credential.backends.sql  # noqa: F401
import keystone.endpoint_policy.backends.sql  # noqa: F401
import keystone.federation.backends.sql  # noqa: F401
import keystone.identity.backends.sql_model  # noqa: F401
import keystone.identity.mapping_backends.sql  # noqa: F401
import keystone.limit.backends.sql  # noqa: F401
import keystone.oauth1.backends.sql  # noqa: F401
import keystone.policy.backends.sql  # noqa: F401
import keystone.resource.backends.sql_model  # noqa: F401
import keystone.resource.config_backends.sql  # noqa: F401
import keystone.revoke.backends.sql  # noqa: F401
import keystone.trust.backends.sql  # noqa: F401

CONF = keystone.conf.CONF
LOG = logging.getLogger(__name__)


class KeystoneModelsMigrationsSync(test_migrations.ModelsMigrationsSync):
    """Test sqlalchemy-migrate migrations."""

    # Migrations can take a long time, particularly on underpowered CI nodes.
    # Give them some breathing room.
    TIMEOUT_SCALING_FACTOR = 4

    def setUp(self):
        # Ensure BaseTestCase's ConfigureLogging fixture is disabled since
        # we're using our own (StandardLogging).
        with fixtures.EnvironmentVariable('OS_LOG_CAPTURE', '0'):
            super().setUp()

        self.useFixture(log_fixture.get_logging_handle_error_fixture())
        self.useFixture(ksfixtures.WarningsFixture())
        self.useFixture(ksfixtures.StandardLogging())

        self.engine = enginefacade.writer.get_engine()

        # Configure our connection string in CONF and enable SQLite fkeys
        db_options.set_defaults(CONF, connection=self.engine.url)

    def db_sync(self, engine):
        upgrades.offline_sync_database_to_version(engine=engine)

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata

    def include_object(self, object_, name, type_, reflected, compare_to):
        if type_ == 'table':
            # migrate_version is a sqlalchemy-migrate control table and
            # isn't included in the models
            if name == 'migrate_version':
                return False

            # This is created in tests and isn't a "real" table
            if name == 'test_table':
                return False

            # FIXME(stephenfin): This was dropped in commit 93aff6e42 but the
            # migrations were never adjusted
            if name == 'token':
                return False

        return True

    def filter_metadata_diff(self, diff):
        """Filter changes before assert in test_models_sync().

        :param diff: a list of differences (see `compare_metadata()` docs for
            details on format)
        :returns: a list of differences
        """
        new_diff = []
        for element in diff:
            # The modify_foo elements are lists; everything else is a tuple
            if isinstance(element, list):
                if element[0][0] == 'modify_nullable':
                    if (element[0][2], element[0][3]) in (
                        ('credential', 'encrypted_blob'),
                        ('credential', 'key_hash'),
                        ('federated_user', 'user_id'),
                        ('federated_user', 'idp_id'),
                        ('local_user', 'user_id'),
                        ('nonlocal_user', 'user_id'),
                        ('password', 'local_user_id'),
                    ):
                        continue  # skip

                if element[0][0] == 'modify_default':
                    if (element[0][2], element[0][3]) in (
                        ('password', 'created_at_int'),
                        ('password', 'self_service'),
                        ('project', 'is_domain'),
                        ('service_provider', 'relay_state_prefix'),
                    ):
                        continue  # skip
            else:
                if element[0] == 'add_constraint':
                    if (
                        element[1].table.name,
                        [x.name for x in element[1].columns],
                    ) in (
                        ('project_tag', ['project_id', 'name']),
                        (
                            'trust',
                            [
                                'trustor_user_id',
                                'trustee_user_id',
                                'project_id',
                                'impersonation',
                                'expires_at',
                            ],
                        ),
                    ):
                        continue  # skip

                # FIXME(stephenfin): These have a different name on PostgreSQL.
                # Resolve by renaming the constraint on the models.
                if element[0] == 'remove_constraint':
                    if (
                        element[1].table.name,
                        [x.name for x in element[1].columns],
                    ) in (
                        ('access_rule', ['external_id']),
                        (
                            'trust',
                            [
                                'trustor_user_id',
                                'trustee_user_id',
                                'project_id',
                                'impersonation',
                                'expires_at',
                                'expires_at_int',
                            ],
                        ),
                    ):
                        continue  # skip

                # FIXME(stephenfin): These indexes are present in the
                # migrations but not on the equivalent models. Resolve by
                # updating the models.
                if element[0] == 'add_index':
                    if (
                        element[1].table.name,
                        [x.name for x in element[1].columns],
                    ) in (
                        ('access_rule', ['external_id']),
                        ('access_rule', ['user_id']),
                        ('revocation_event', ['revoked_at']),
                        ('system_assignment', ['actor_id']),
                        ('user', ['default_project_id']),
                    ):
                        continue  # skip

                # FIXME(stephenfin): These indexes are present on the models
                # but not in the migrations. Resolve by either removing from
                # the models or adding new migrations.
                if element[0] == 'remove_index':
                    if (
                        element[1].table.name,
                        [x.name for x in element[1].columns],
                    ) in (
                        ('access_rule', ['external_id']),
                        ('access_rule', ['user_id']),
                        ('access_token', ['consumer_id']),
                        ('endpoint', ['service_id']),
                        ('revocation_event', ['revoked_at']),
                        ('user', ['default_project_id']),
                        ('user_group_membership', ['group_id']),
                        (
                            'trust',
                            [
                                'trustor_user_id',
                                'trustee_user_id',
                                'project_id',
                                'impersonation',
                                'expires_at',
                                'expires_at_int',
                            ],
                        ),
                        (),
                    ):
                        continue  # skip

                # FIXME(stephenfin): These fks are present in the
                # migrations but not on the equivalent models. Resolve by
                # updating the models.
                if element[0] == 'add_fk':
                    if (element[1].table.name, element[1].column_keys) in (
                        (
                            'application_credential_access_rule',
                            ['access_rule_id'],
                        ),
                        ('limit', ['registered_limit_id']),
                        ('registered_limit', ['service_id']),
                        ('registered_limit', ['region_id']),
                        ('endpoint', ['region_id']),
                    ):
                        continue  # skip

                # FIXME(stephenfin): These indexes are present on the models
                # but not in the migrations. Resolve by either removing from
                # the models or adding new migrations.
                if element[0] == 'remove_fk':
                    if (element[1].table.name, element[1].column_keys) in (
                        (
                            'application_credential_access_rule',
                            ['access_rule_id'],
                        ),
                        ('endpoint', ['region_id']),
                        ('assignment', ['role_id']),
                    ):
                        continue  # skip

            new_diff.append(element)

        return new_diff


class TestModelsSyncSQLite(
    KeystoneModelsMigrationsSync,
    test_fixtures.OpportunisticDBTestMixin,
    base.BaseTestCase,
):
    pass


class TestModelsSyncMySQL(
    KeystoneModelsMigrationsSync,
    test_fixtures.OpportunisticDBTestMixin,
    base.BaseTestCase,
):
    FIXTURE = test_fixtures.MySQLOpportunisticFixture


class TestModelsSyncPostgreSQL(
    KeystoneModelsMigrationsSync,
    test_fixtures.OpportunisticDBTestMixin,
    base.BaseTestCase,
):
    FIXTURE = test_fixtures.PostgresqlOpportunisticFixture


class KeystoneModelsMigrationsLegacySync(KeystoneModelsMigrationsSync):
    """Test that the models match the database after old migrations are run."""

    def db_sync(self, engine):
        # the 'upgrades._db_sync' method will not use the legacy
        # sqlalchemy-migrate-based migration flow unless the database is
        # already controlled with sqlalchemy-migrate, so we need to manually
        # enable version controlling with this tool to test this code path
        for branch in (
            upgrades.EXPAND_BRANCH,
            upgrades.DATA_MIGRATION_BRANCH,
            upgrades.CONTRACT_BRANCH,
        ):
            repository = upgrades._find_migrate_repo(branch)
            migrate_api.version_control(
                engine, repository, upgrades.MIGRATE_INIT_VERSION)

        # now we can apply migrations as expected and the legacy path will be
        # followed
        super().db_sync(engine)


class TestModelsLegacySyncSQLite(
    KeystoneModelsMigrationsLegacySync,
    test_fixtures.OpportunisticDBTestMixin,
    base.BaseTestCase,
):
    pass


class TestModelsLegacySyncMySQL(
    KeystoneModelsMigrationsLegacySync,
    test_fixtures.OpportunisticDBTestMixin,
    base.BaseTestCase,
):
    FIXTURE = test_fixtures.MySQLOpportunisticFixture


class TestModelsLegacySyncPostgreSQL(
    KeystoneModelsMigrationsLegacySync,
    test_fixtures.OpportunisticDBTestMixin,
    base.BaseTestCase,
):
    FIXTURE = test_fixtures.PostgresqlOpportunisticFixture


class KeystoneMigrationsWalk(
    test_fixtures.OpportunisticDBTestMixin,
):

    # Migrations can take a long time, particularly on underpowered CI nodes.
    # Give them some breathing room.
    TIMEOUT_SCALING_FACTOR = 4

    def setUp(self):
        super().setUp()
        self.engine = enginefacade.writer.get_engine()
        self.config = upgrades._find_alembic_conf()
        self.init_version = upgrades.ALEMBIC_INIT_VERSION

    def _migrate_up(self, connection, revision):
        if revision == self.init_version:  # no tests for the initial revision
            alembic_api.upgrade(self.config, revision)
            return

        self.assertIsNotNone(
            getattr(self, '_check_%s' % revision, None),
            (
                'DB Migration %s does not have a test; you must add one'
            ) % revision,
        )

        pre_upgrade = getattr(self, '_pre_upgrade_%s' % revision, None)
        if pre_upgrade:
            pre_upgrade(connection)

        alembic_api.upgrade(self.config, revision)

        post_upgrade = getattr(self, '_check_%s' % revision, None)
        if post_upgrade:
            post_upgrade(connection)

    def _pre_upgrade_e25ffa003242(self, connection):
        """This is a no-op migration."""
        pass

    def _check_e25ffa003242(self, connection):
        """This is a no-op migration."""
        pass

    def _pre_upgrade_29e87d24a316(self, connection):
        """This is a no-op migration."""
        pass

    def _check_29e87d24a316(self, connection):
        """This is a no-op migration."""
        pass

    def test_single_base_revision(self):
        """Ensure we only have a single base revision.

        There's no good reason for us to have diverging history, so validate
        that only one base revision exists. This will prevent simple errors
        where people forget to specify the base revision. If this fail for
        your change, look for migrations that do not have a 'revises' line in
        them.
        """
        script = alembic_script.ScriptDirectory.from_config(self.config)
        self.assertEqual(1, len(script.get_bases()))

    def test_head_revisions(self):
        """Ensure we only have a two head revisions.

        There's no good reason for us to have diverging history beyond the
        expand and contract branches, so validate that only these head
        revisions exist. This will prevent merge conflicts adding additional
        head revision points. If this fail for your change, look for migrations
        with the duplicate 'revises' line in them.
        """
        script = alembic_script.ScriptDirectory.from_config(self.config)
        self.assertEqual(2, len(script.get_heads()))

    def test_walk_versions(self):
        with self.engine.begin() as connection:
            self.config.attributes['connection'] = connection
            script = alembic_script.ScriptDirectory.from_config(self.config)
            revisions = [x.revision for x in script.walk_revisions()]

            # for some reason, 'walk_revisions' gives us the revisions in
            # reverse chronological order so we have to invert this
            revisions.reverse()
            self.assertEqual(revisions[0], self.init_version)

            for revision in revisions:
                LOG.info('Testing revision %s', revision)
                self._migrate_up(connection, revision)

    def _get_head_from_file(self, branch):
        path = os.path.join(
            os.path.dirname(upgrades.__file__),
            'migrations',
            'versions',
            f'{branch.upper()}_HEAD',
        )

        with open(path) as fh:
            return fh.read().strip()

    def test_db_version_alembic(self):
        upgrades.offline_sync_database_to_version(engine=self.engine)

        for branch in (upgrades.EXPAND_BRANCH, upgrades.CONTRACT_BRANCH):
            head = self._get_head_from_file(branch)
            self.assertEqual(head, upgrades.get_db_version(branch))


class TestMigrationsWalkSQLite(
    KeystoneMigrationsWalk,
    test_fixtures.OpportunisticDBTestMixin,
    unit.TestCase,
):
    pass


class TestMigrationsWalkMySQL(
    KeystoneMigrationsWalk,
    test_fixtures.OpportunisticDBTestMixin,
    unit.TestCase,
):
    FIXTURE = test_fixtures.MySQLOpportunisticFixture


class TestMigrationsWalkPostgreSQL(
    KeystoneMigrationsWalk,
    test_fixtures.OpportunisticDBTestMixin,
    unit.TestCase,
):
    FIXTURE = test_fixtures.PostgresqlOpportunisticFixture
