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

import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    ASSIGNMENT_TABLE_NAME = 'assignment'
    TMP_ASSIGNMENT_TABLE_NAME = 'tmp_assignment'
    assignment_table = sql.Table(ASSIGNMENT_TABLE_NAME, meta, autoload=True)
    tmp_assignment_table = sql.Table(
        TMP_ASSIGNMENT_TABLE_NAME, meta, autoload=True
    )

    session = sql.orm.sessionmaker(bind=migrate_engine)()

    assignments = list(assignment_table.select().execute())
    for assignment in assignments:
        values = dict(assignment)
        values['assignment_type'] = values.pop('type')
        insert = tmp_assignment_table.insert().values(values)
        session.execute(insert)
        session.commit()
