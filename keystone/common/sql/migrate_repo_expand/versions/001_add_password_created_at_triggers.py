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

import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sql.orm.sessionmaker(bind=migrate_engine)()

    if migrate_engine.name == 'sqlite' or migrate_engine.name == 'mysql':
        stmt = 'DROP TRIGGER IF EXISTS password_created_at;'
        stmt += 'CREATE TRIGGER password_created_at AFTER INSERT ON password'
        stmt += 'FOR EACH ROW'
        stmt += 'BEGIN'
        stmt += '    UPDATE password SET created_at = NOW() WHERE id = NEW.id;'
        stmt += 'END;'
        session.execute(stmt)
    # TODO(rderose): add postgresql trigger
