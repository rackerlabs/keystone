# Copyright 2014 Mirantis.inc
# All Rights Reserved.
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

"""The version #2 had missed primary key. The fix in the #2 migration was
required due to critical bug: the migration couldn't be applied, it has raise
OperationalError on both MySQL(errno: 150) and PostgreSQL. The fix for the #2
migration has implemented. Also required this migration script to fix an
existing SQLite driven deployments."""

from migrate.changeset import constraint
import sqlalchemy as sql


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    endpoint_group_table = sql.Table('endpoint_group', meta, autoload=True)
    if not endpoint_group_table.primary_key:
        pk = constraint.PrimaryKeyConstraint(endpoint_group_table.c.id)
        pk.create(migrate_engine)


def downgrade(migrate_engine):
    """Downgrade of this migration doesn't implies a change reversion.

    This migration is the fix for previously deployed instances where was
    applied the #2 migration before it fixed. The #2 migration has already
    fixed and contains the change.
    """
    pass
