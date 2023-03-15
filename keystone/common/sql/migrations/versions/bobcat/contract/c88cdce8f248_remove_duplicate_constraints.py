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

"""Remove duplicate constraints.

Revision ID: c88cdce8f248
Revises: 99de3849d860
Create Date: 2023-03-15 13:17:44.060715
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'c88cdce8f248'
down_revision = '99de3849d860'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # This only affects MySQL - PostgreSQL and SQLite were smart enough to
    # ignore the duplicate constraints
    if bind.engine.name != 'mysql':
        return

    with op.batch_alter_table('project_tag', schema=None) as batch_op:
        # We would normally just use drop_index like so:
        #
        #   batch_op.drop_index('project_id')
        #
        # However, the index wasn't explicitly named so it has two potential
        # names: if it was created by alembic, it will leave things up to
        # the backend (which on MySQL means the index will have the same name
        # as the first column the index covers [1]), but if it was created by
        # sqlalchemy-migrate then '{table_name}_{first_column_name}_key' will
        # be used [2].
        #
        # [1] https://dba.stackexchange.com/a/160712
        # [2] https://opendev.org/x/sqlalchemy-migrate/src/commit/5d1f322542cd8eb42381612765be4ed9ca8105ec/migrate/changeset/constraint.py#L199  # noqa: E501
        for index_name in ('project_id', 'project_tag_project_id_key'):
            batch_op.execute(
                'ALTER TABLE project_tag DROP CONSTRAINT IF EXISTS %s'
                % index_name
            )
