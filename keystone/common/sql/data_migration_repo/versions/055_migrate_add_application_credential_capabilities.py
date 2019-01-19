# Copyright 2019 SUSE Linux GmbH
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


import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


# Insert a default capability of null values, which will indicate a fully
# permissive capability, the default when none is provided by the user.
def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    maker = sessionmaker(bind=migrate_engine)
    session = maker()

    capability = sql.Table('capability', meta, autoload=True)

    allow_all_capability = {
        'service': None,
        'request_path': None,
        'request_method': None
    }

    new_row = capability.insert().values(**allow_all_capability)
    session.execute(new_row)
    session.commit()
