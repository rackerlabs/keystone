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

"""Add index in revocation_event

Revision ID: e19ee1de655c
Revises: 47147121
Create Date: 2024-09-18 09:41:52.325730
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'e19ee1de655c'
down_revision = '47147121'
branch_labels = None
depends_on = None

def upgrade():
    op.create_index('idx_revocation_event_project_id_user_id', 'revocation_event', ['project_id,user_id'])
    op.create_index('idx_revocation_event_composite', 'revocation_event', ['issued_before,user_id,project_id,audit_id'])

def downgrade():
    op.drop_index('idx_revocation_event_project_id_user_id', 'revocation_event')
    op.drop_index('idx_revocation_event_composite', 'revocation_event')
