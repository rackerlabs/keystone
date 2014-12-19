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
import sys

import migrate
from migrate import exceptions
from oslo.db.sqlalchemy import migration
from oslo.db.sqlalchemy.migration_cli import manager as migration_manager
from oslo.serialization import jsonutils
from oslo.utils import importutils
import six
import sqlalchemy

from keystone.common import sql
from keystone.common.sql import migrate_repo
from keystone import config
from keystone import contrib
from keystone import exception
from keystone.i18n import _


CONF = config.CONF
DEFAULT_EXTENSIONS = ['revoke']


def get_default_domain():
    # Return the reference used for the default domain structure during
    # sql migrations.
    return {
        'id': CONF.identity.default_domain_id,
        'name': 'Default',
        'enabled': True,
        'extra': jsonutils.dumps({'description': 'Owns users and tenants '
                                                 '(i.e. projects) available '
                                                 'on Identity API v2.'})}


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
    """Renames tables with foreign key constraints.

    Tables are renamed after first removing constraints. The constraints are
    replaced after the rename is complete.

    This works on databases that don't support renaming tables that have
    constraints on them (DB2).

    `renames` is a dict, mapping {'to_table_name': from_table, ...}
    """

    if engine.name != 'sqlite':
        # Sqlite doesn't support constraints, so nothing to remove.
        remove_constraints(constraints)

    for to_table_name in renames:
        from_table = renames[to_table_name]
        from_table.rename(to_table_name)

    if engine != 'sqlite':
        add_constraints(constraints)


def find_repo(repo_name, package):
    path = os.path.abspath(os.path.join(
        os.path.dirname(package.__file__), repo_name))
    if os.path.isdir(path):
        return path
    raise exception.MigrationNotProvided(package.__name__, path)


def _fix_migration_37(engine):
    """Fix the region table to be InnoDB and Charset UTF8.

    This function is to work around bug #1334779. This has occurred because
    the original migration 37 did not specify InnoDB and charset utf8. Due
    to the sanity_check, a deployer can get wedged here and require manual
    database changes to fix.
    """
    # NOTE(morganfainberg): Extra defensive here, check to make sure we really
    # are mysql before trying to perform the alters.
    if engine.name == 'mysql':
        # * Make sure the engine is InnoDB
        engine.execute('ALTER TABLE region Engine=InnoDB')
        # * Make sure the character set is utf8
        engine.execute('ALTER TABLE region CONVERT TO CHARACTER SET utf8')


def _prepare_migrate_repo(migrate_path, version=None):
    engine = sql.get_engine()
    try:
        migration.db_version_control(engine, migrate_path, version)
    # Register the repo with the version control API
    # If it already knows about the repo, it will throw
    # an exception that we can safely ignore
    except exceptions.DatabaseAlreadyControlledError:
        pass


def get_migration_manager(extension=None):
    if extension:
        try:
            package_name = '.'.join((contrib.__name__, extension))
            package = importutils.import_module(package_name)
        except ImportError:
            raise ImportError(_("%s extension does not exist.")
                              % package_name)
        init_version = 0
    else:
        package = sql
        init_version = migrate_repo.DB_INIT_VERSION

    # sqlalchemy-migrate repo must exist
    migrate_path = find_repo('migrate_repo', package)
    migration_config = {
        'migration_repo_path': migrate_path,
        'init_version': init_version,
        'db_url': CONF.database.connection,
    }

    # NOTE(breton): sqlalchemy-migrate requires a database to be assigned to a
    # repository. Migration helpers in oslo_db fail to do it when there is
    # multiple repositories. This is a workaround for this behaviour
    _prepare_migrate_repo(migrate_path, init_version)

    # Alembic repos might still not exist, so it shouldn't fail if they don't
    try:
        alembic_path = find_repo('alembic', package)
    except exception.MigrationNotProvided:
        alembic_path = None
    if alembic_path:
        migration_config['alembic_ini_path'] = os.path.join(alembic_path,
                                                            'alembic.ini')
        migration_config['alembic_repo_path'] = alembic_path

    manager = migration_manager.MigrationManager(migration_config)
    return manager


def sync_extension(method, version, extension):
    manager = get_migration_manager(extension)
    getattr(manager, method)(version)


def sync_common(method, version):
    engine = sql.get_engine()
    manager = get_migration_manager()
    try:
        getattr(manager, method)(version)
    except ValueError:
        # NOTE(morganfainberg): ValueError is raised from the sanity check (
        # verifies that tables are utf8 under mysql). The region table was not
        # initially built with InnoDB and utf8 as part of the table arguments
        # when the migration was initially created. Bug #1334779 is a scenario
        # where the deployer can get wedged, unable to upgrade or downgrade.
        # This is a workaround to "fix" that table if we're under MySQL.
        if engine.name == 'mysql' and six.text_type(get_db_version()) == '37':
            _fix_migration_37(engine)
            # Try the migration a second time now that we've done the
            # un-wedge work.
            getattr(manager, method)(version)
        else:
            raise


def sync_database_to_version(method, version=None, extension=None):
    if not extension:
        sync_common(method, version)
        # If version is greater than 0, it is for the common
        # repository only, and only that will be synchronized.
        if version is None:
            for default_extension in DEFAULT_EXTENSIONS:
                sync_extension(method, version, default_extension)
    else:
        sync_extension(method, version, extension)


def get_db_version(extension=None):
    manager = get_migration_manager(extension)
    return manager.version()


def print_db_version(extension=None):
    try:
        print(get_db_version(extension))
    except exception.MigrationNotProvided as e:
        print(e)
        sys.exit(1)


def stamp(version=None, extension=None):
    manager = get_migration_manager(extension)
    manager.stamp(version)
