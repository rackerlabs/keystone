# Copyright 2013 OpenStack Foundation
# Copyright 2013 Red Hat, Inc.
# All Rights Reserved.
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

import os

import migrate
from migrate import exceptions
from oslo_db.sqlalchemy import migration
import six
import sqlalchemy

from keystone.common import sql
from keystone.common.sql import force_migrations
from keystone.common.sql import migration_control
from keystone.common.sql import migration_phase_sql
import keystone.conf
from keystone import exception
from keystone.i18n import _


CONF = keystone.conf.CONF


#  Different RDBMSs use different schemes for naming the Foreign Key
#  Constraints.  SQLAlchemy does not yet attempt to determine the name
#  for the constraint, and instead attempts to deduce it from the column.
#  This fails on MySQL.
def get_constraints_names(table, column_name):
    fkeys = [fk.name for fk in table.constraints
             if (isinstance(fk, sqlalchemy.ForeignKeyConstraint) and
                 column_name in fk.columns)]
    return fkeys


#  remove_constraints and add_constraints both accept a list of dictionaries
#  that contain:
#  {'table': a sqlalchemy table. The constraint is added to dropped from
#           this table.
#  'fk_column': the name of a column on the above table,  The constraint
#               is added to or dropped from this column
#  'ref_column':a sqlalchemy column object.  This is the reference column
#               for the constraint.
def remove_constraints(constraints):
    for constraint_def in constraints:
        constraint_names = get_constraints_names(constraint_def['table'],
                                                 constraint_def['fk_column'])
        for constraint_name in constraint_names:
            migrate.ForeignKeyConstraint(
                columns=[getattr(constraint_def['table'].c,
                                 constraint_def['fk_column'])],
                refcolumns=[constraint_def['ref_column']],
                name=constraint_name).drop()


def add_constraints(constraints):
    for constraint_def in constraints:

        if constraint_def['table'].kwargs.get('mysql_engine') == 'MyISAM':
            # Don't try to create constraint when using MyISAM because it's
            # not supported.
            continue

        ref_col = constraint_def['ref_column']
        ref_engine = ref_col.table.kwargs.get('mysql_engine')
        if ref_engine == 'MyISAM':
            # Don't try to create constraint when using MyISAM because it's
            # not supported.
            continue

        migrate.ForeignKeyConstraint(
            columns=[getattr(constraint_def['table'].c,
                             constraint_def['fk_column'])],
            refcolumns=[constraint_def['ref_column']]).create()


def rename_tables_with_constraints(renames, constraints, engine):
    """Rename tables with foreign key constraints.

    Tables are renamed after first removing constraints. The constraints are
    replaced after the rename is complete.

    This works on databases that don't support renaming tables that have
    constraints on them (DB2).

    `renames` is a dict, mapping {'to_table_name': from_table, ...}
    """
    if engine.name != 'sqlite':
        # SQLite doesn't support constraints, so nothing to remove.
        remove_constraints(constraints)

    for to_table_name in renames:
        from_table = renames[to_table_name]
        from_table.rename(to_table_name)

    if engine != 'sqlite':
        add_constraints(constraints)


def find_migrate_repo(package=None, repo_name='migrate_repo'):
    package = package or sql
    path = os.path.abspath(os.path.join(
        os.path.dirname(package.__file__), repo_name))
    if os.path.isdir(path):
        return path
    raise exception.MigrationNotProvided(package.__name__, path)


def _sync_common_repo(version):
    abs_path = find_migrate_repo()
    init_version = get_init_version()
    with sql.session_for_write() as session:
        engine = session.get_bind()
        _assert_not_schema_downgrade(version=version)
        migration.db_sync(engine, abs_path, version=version,
                          init_version=init_version, sanity_check=False)


def get_init_version(abs_path=None):
    """Get the initial version of a migrate repository.

    :param abs_path: Absolute path to migrate repository.
    :return:         initial version number or None, if DB is empty.
    """
    if abs_path is None:
        abs_path = find_migrate_repo()

    repo = migrate.versioning.repository.Repository(abs_path)

    # Sadly, Repository has a `latest` but not an `oldest`.
    # The value is a VerNum object which needs to be converted into an int.
    oldest = int(min(repo.versions.versions))

    if oldest < 1:
        return None

    # The initial version is one less
    return oldest - 1


def _assert_not_schema_downgrade(version=None):
    if version is not None:
        try:
            current_ver = int(six.text_type(get_db_version()))
            if int(version) < current_ver:
                raise migration.exception.DbMigrationError(
                    _("Unable to downgrade schema"))
        except exceptions.DatabaseNotControlledError:  # nosec
            # NOTE(morganfainberg): The database is not controlled, this action
            # cannot be a downgrade.
            pass


MIGRATION_STATUS_STARTED = 'Started'
MIGRATION_STATUS_UPGRADE_COMPLETED = 'Upgrade Completed'
MIGRATION_STATUS_RESTART_COMPLETED = 'Restart Completed'
MIGRATION_STATUS_FORCE_MIGRATE_COMPLETED = 'Force Migrate Completed'
MIGRATION_STATUS_COMPLETED = 'Completed'

VERSION_THAT_CREATES_MIGRATION_STATUS_TABLE = 108

PHASE_STATE_DIAGRAM = {
    MIGRATION_STATUS_STARTED: {
        'next': MIGRATION_STATUS_UPGRADE_COMPLETED,
        'help': _("You are currently in the code upgrading phase. The "
                  "next command in the sequence should be "
                  "'keystone-manage db_sync --rolling-upgrade-complete' once "
                  "the nodes have been upgraded and started.")
    },
    MIGRATION_STATUS_UPGRADE_COMPLETED: {
        'next': MIGRATION_STATUS_RESTART_COMPLETED,
        'help': _("You are currently in the phase of restarting after "
                  "upgrading each of your keystone nodes. The next command in "
                  "the sequence should be "
                  "'keystone-manage db_sync --rolling-restart-complete' once "
                  "the nodes have been restarted again.")
    },
    MIGRATION_STATUS_RESTART_COMPLETED: {
        'next': MIGRATION_STATUS_FORCE_MIGRATE_COMPLETED,
        'help': _("You are currently in the phase of background data "
                  "migration after upgrading your keystone nodes. The next "
                  "command in the sequence should be "
                  "'keystone-manage db_sync --force-migration-complete' to "
                  "complete this phase.")
    },
    MIGRATION_STATUS_FORCE_MIGRATE_COMPLETED: {
        'next': MIGRATION_STATUS_COMPLETED,
        'help': _("You have completed all the data migration. The next (and "
                  "last) command in the sequence should be "
                  "'keystone-manage db_sync --contract' to remove any "
                  "database structures that are no longer needed.")
    },
    MIGRATION_STATUS_COMPLETED: {
        'next': MIGRATION_STATUS_STARTED,
        'help': _("You are not currently undertaking a migration. The first "
                  "command in the sequence should be "
                  "'keystone-manage db_sync --expand'")
    },
}


def offline_sync_database_to_version(version=None):
    """Perform and off-line sync of the database.

    Migrate the database upto the latest version, allowing a migration across
    two release versions. In addition, run all the tidy-up, force data
    migration and contract phases to ensure the resulting database is the same
    irrespective of whether an offline or online (i.e. rolling) upgrade was
    performed.

    If a version is specified then only migrate the database up to that
    version. Downgrading is not supported. If version is specified, then only
    the main database migration is carried out - and the tidy-up, force data
    migration and contract phases will NOT be run.

    """
    _sync_common_repo(version)

    if not version:
        # We could call each of the individual methods for the various
        # migration phases to drive the whole migration. However, one of the
        # goals of still supporting the raw db_sync command is to try and
        # force through an off-line upgrade if the operator has run into issues
        # with an on-line rolling upgrade. So instead we duplicate the actions
        # and then stamp the status row at the end.

        # TODO(henry-nash): Currently this will work for a 1 or 2 release
        # upgrade to Newton, but won't work for a 2 release upgrade to Ocata.
        force_migrations.tidy_up_migration(migration_control.LATEST_RELEASE)
        force_migrations.force_data_migration(migration_control.LATEST_RELEASE)
        # TODO(henry-nash): add call to contract phase here
        next_status = {'current_phase': MIGRATION_STATUS_COMPLETED,
                       'current_version': migration_control.LATEST_RELEASE,
                       'migrating_to_version': migration_control.NO_RELEASE}
        migration_phase = migration_phase_sql.MigrationPhase()
        try:
            migration_phase.update_migration_status(next_status)
        except exception.NotFound:
            migration_phase.create_migration_status(next_status)


def get_db_version():
    with sql.session_for_write() as session:
        return migration.db_version(session.get_bind(),
                                    find_migrate_repo(),
                                    get_init_version())


def print_db_version():
    print(get_db_version())


def _assert_under_migration_control():
    if get_db_version() < VERSION_THAT_CREATES_MIGRATION_STATUS_TABLE:
        print(PHASE_STATE_DIAGRAM[MIGRATION_STATUS_COMPLETED]['help'])
        raise RuntimeError


def _assert_correct_migration_phase(current_status, next_status):
    if current_status is None:
        print(_("No upgrade is in progress, you need to start with "
                "'keystone-manage db_sync --expand'"))
        raise RuntimeError

    current_phase = current_status['current_phase']
    if next_status != PHASE_STATE_DIAGRAM[current_phase]['next']:
        print(_('You are trying to execute an upgrade phase out of order'))
        print(PHASE_STATE_DIAGRAM[current_phase]['help'])
        raise RuntimeError


def _assert_release_in_range(current_version, allowable_version_steps):
    new = migration_control.RELEASE_SEQUENCE[migration_control.LATEST_RELEASE]
    current = migration_control.RELEASE_SEQUENCE[current_version]
    if new - current > allowable_version_steps:
        print(_('You are trying to migrate across too broad a range of '
                'versions. You will need to migrate in smaller version '
                'steps.'))
        raise RuntimeError


def _get_migration_status(driver):
    """Get the migration status.

    Return None if either the table does not exist yet or the row does not yet
    exist - meaning we have not yet run the first migration that supported
    rolling upgrades.

    """
    try:
        current_status = driver.get_migration_status()
    except exception.NotFound:
        pass
    return current_status


def migration_expand():
    """Expand the database ahead of code upgrade.

    Since we currently do not support on-the-fly migration at the point of
    object access, we run all the migration scripts now.

    This is run manually by the keystone-manage command before the first
    keystone node is migrated to the latest release.

    """
    next_status = {'migrating_to_version': migration_control.LATEST_RELEASE,
                   'current_phase': MIGRATION_STATUS_STARTED}
    if get_db_version() < VERSION_THAT_CREATES_MIGRATION_STATUS_TABLE:
        _assert_release_in_range(migration_control.EARLIER_RELEASE, 1)
        _sync_common_repo(version=None)
        next_status['current_version'] = migration_control.EARLIER_RELEASE
        migration_phase = migration_phase_sql.MigrationPhase()
        migration_phase.create_migration_status(next_status)
    else:
        migration_phase = migration_phase_sql.MigrationPhase()
        current_status = _get_migration_status(migration_phase)
        # Technically if the table exists, the status row should also exist,
        # but just in case this creation somehow failed, we check and if
        # necessary re-create it here.
        if current_status is None:
            next_status['current_version'] = migration_control.EARLIER_RELEASE
            _assert_release_in_range(migration_control.EARLIER_RELEASE, 1)
            _sync_common_repo(version=None)
            migration_phase.create_migration_status(next_status)
        else:
            _assert_correct_migration_phase(current_status,
                                            MIGRATION_STATUS_STARTED)
            _assert_release_in_range(migration_control.LATEST_RELEASE, 1)
            _sync_common_repo(version=None)
            migration_phase.update_migration_status(next_status)


def rolling_upgrade_complete():
    """Mark the database phase as all nodes running new code.

    This is run manually by the keystone-manage command once the
    last keystone node is upgraded to the new code release. Any
    tidy-up migration code can be run here, since we know that there are
    no nodes left running the old release.

    """
    _assert_under_migration_control()
    migration_phase = migration_phase_sql.MigrationPhase()
    current_status = _get_migration_status(migration_phase)
    _assert_correct_migration_phase(current_status,
                                    MIGRATION_STATUS_UPGRADE_COMPLETED)
    force_migrations.tidy_up_migration(migration_control.LATEST_RELEASE)
    next_status = {'current_phase': MIGRATION_STATUS_UPGRADE_COMPLETED}
    migration_phase.update_migration_status(next_status)


def rolling_restart_complete():
    """Mark the database phase as all nodes aware of upgrade is complete.

    This is run manually by the keystone-manage command once the
    last keystone node is restarted following the setting
    rolling_upgrade_complete.

    """
    _assert_under_migration_control()
    migration_phase = migration_phase_sql.MigrationPhase()
    current_status = _get_migration_status(migration_phase)
    _assert_correct_migration_phase(current_status,
                                    MIGRATION_STATUS_RESTART_COMPLETED)
    next_status = {'current_phase': MIGRATION_STATUS_RESTART_COMPLETED}
    migration_phase.update_migration_status(next_status)


def force_migration_complete():
    """Tidy the database after migration.

    This is run manually by the keystone-manage command once all keystone
    nodes have been migrated to the latest release.

    This method should ensure all data has been migrated to its new locations
    as well as ensuring that any data inconsistencies that could have been
    created during a rolling upgrade are tidied up.

    """
    _assert_under_migration_control()
    migration_phase = migration_phase_sql.MigrationPhase()
    current_status = _get_migration_status(migration_phase)
    _assert_correct_migration_phase(current_status,
                                    MIGRATION_STATUS_FORCE_MIGRATE_COMPLETED)
    force_migrations.force_data_migration(migration_control.LATEST_RELEASE)
    next_status = {'current_phase': MIGRATION_STATUS_FORCE_MIGRATE_COMPLETED}
    migration_phase.update_migration_status(next_status)


def migration_contract():
    """Contract the database.

    This is run manually by the keystone-manage command once all nodes are
    running code that no longer looks at old tables/columns.

    """
    _assert_under_migration_control()
    migration_phase = migration_phase_sql.MigrationPhase()
    current_status = _get_migration_status(migration_phase)
    _assert_correct_migration_phase(current_status,
                                    MIGRATION_STATUS_COMPLETED)
    if current_status['current_version'] == migration_control.EARLIER_RELEASE:
        # Nothing to do, since we didn't support contraction then
        pass
    else:
        # TODO(henry-nash): Migrate contract repo here.
        pass
    next_status = {'current_phase': MIGRATION_STATUS_COMPLETED,
                   'current_version': migration_control.LATEST_RELEASE,
                   'migrating_to_version': migration_control.NO_RELEASE}
    migration_phase.update_migration_status(next_status)


def migration_status():
    """Print the status of the migration."""
    _assert_under_migration_control()
    migration_phase = migration_phase_sql.MigrationPhase()
    current_status = migration_phase.get_migration_status()
    print(PHASE_STATE_DIAGRAM[current_status['current_phase']]['help'])
