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

from oslo_serialization import jsonutils
import sqlalchemy as sql

_TRUST_TABLE_NAME = 'trust'

def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    trust_table = sql.Table(_TRUST_TABLE_NAME, meta, autoload=True)
    redelegated_trust_id_column = sql.Column('redelegated_trust_id',
                                             sql.String(64))

    # Create new column to store the redelegated trust id
    trust_table.create_column(redelegated_trust_id_column)
    trust_list = list(trust_table.select().execute())

    # Loop through all the trust and move the redelegeated trust id out of
    # extas.
    for trust in trust_list:
        if trust.extra is not None:
            extra_dict = jsonutils.loads(trust.extra)
        else:
            extra_dict = {}

        if 'redelegated_trust_id' in extra_dict:
            redelegated_trust_id = extra_dict['redelegated_trust_id']
            # Remove key from dictionary
            extra_dict.pop('redelegated_trust_id', None)
            new_values = {
                'extra': jsonutils.dumps(extra_dict)
            }
            if redelegated_trust_id:
                new_values['redelegated_trust_id'] = redelegated_trust_id
            f = trust_table.c.id == trust.id
            update = trust_table.update().where(f).values(new_values)
            migrate_engine.execute(update)
