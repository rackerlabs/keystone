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

"""Add ip_allowlist_entry table

Revision ID: a1b2c3d4e5f6
Revises: 742c857f1dfb
Create Date: 2026-04-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '742c857f1dfb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ip_allowlist_entry',
        sa.Column('id', sa.String(64), primary_key=True, nullable=False),
        sa.Column('target_type', sa.String(16), nullable=False),
        sa.Column('target_id', sa.String(64), nullable=False),
        sa.Column('cidr', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            'target_type',
            'target_id',
            'cidr',
            name='uq_ip_allowlist_target_cidr',
        ),
        mysql_engine='InnoDB',
        mysql_charset='utf8',
    )
    op.create_index(
        'ix_ip_allowlist_entry_target',
        'ip_allowlist_entry',
        ['target_type', 'target_id'],
    )
