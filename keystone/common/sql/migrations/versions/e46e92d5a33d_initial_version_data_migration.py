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

"""Initial version

Revision ID: e46e92d5a33d
Revises: 27e647c0fad4
Create Date: 2022-01-13 16:45:04.344732
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.sql

# revision identifiers, used by Alembic.
revision = 'e46e92d5a33d'
down_revision = '27e647c0fad4'
branch_labels = ('data_migration',)
depends_on = None

NULL_DOMAIN_ID = '<<keystone.domain.root>>'


def upgrade():
    def _generate_root_domain_project():
        # Generate a project that will act as a root for all domains, in order
        # for use to be able to use a FK constraint on domain_id. Projects
        # acting as a domain will not reference this as their parent_id, just
        # as domain_id.
        #
        # This special project is filtered out by the driver, so is never
        # visible to the manager or API.

        project_ref = {
            'id': NULL_DOMAIN_ID,
            'name': NULL_DOMAIN_ID,
            'enabled': False,
            'description': '',
            'domain_id': NULL_DOMAIN_ID,
            'is_domain': True,
            'parent_id': None,
            'extra': '{}',
        }
        return project_ref

    bind = op.get_bind()
    meta = sa.MetaData()
    project = sa.Table('project', meta, autoload_with=bind.engine)

    root_domain_project = _generate_root_domain_project()
    op.execute(project.insert().values(**root_domain_project))
