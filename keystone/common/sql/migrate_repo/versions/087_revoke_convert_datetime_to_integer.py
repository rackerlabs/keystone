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

import datetime

from oslo_utils import timeutils
import six
import sqlalchemy as sql


_TABLE_NAME = 'revocation_event'


def _convert_datetimes_to_ints(event):
    # get an epoch datetime object since we will need this in the conversion
    epoch = datetime.datetime.utcfromtimestamp(0)

    d = {'issued_before': event.issued_before,
         'expires_at': event.expires_at,
         'revoked_at': event.revoked_at}

    new_values = {}
    for k, v in six.iteritems(d):
        # only do stuff v is not None
        if not v:
            continue

        # mysql stores datetime objects as strings and sqlite doesn't
        if v and not isinstance(v, datetime.datetime):
            v = timeutils.parse_isotime(v)

        # nuke the tz info because it messes with determining the total seconds
        v = v.replace(tzinfo=None)

        # figure out the number of microseconds since epoch
        timestamp = int((v - epoch).total_seconds() * 1e6)

        # shove the new timestamp integer into the trust reference
        new_values[k + '_int'] = timestamp

    return new_values


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    # get the revocation_event table
    revocation_event_table = sql.Table(_TABLE_NAME, meta, autoload=True)

    # create a new column for issued_at integer timestamps
    issued_before_int = sql.Column('issued_before_int', sql.BigInteger)
    issued_before_int.create(revocation_event_table)

    # create a new column for expires_at integer timestamps
    expires_at_int = sql.Column('expires_at_int', sql.BigInteger)
    expires_at_int.create(revocation_event_table)

    # create a new column for revoked_at integer timestamps
    revoked_at_int = sql.Column('revoked_at_int', sql.BigInteger)
    revoked_at_int.create(revocation_event_table)

    # get all the revocation events
    events = list(revocation_event_table.select().execute())

    for event in events:
        values = _convert_datetimes_to_ints(event)

        # shove the new timestamp integer into the trust reference
        f = revocation_event_table.c.id == event.id
        update = revocation_event_table.update().where(f).values(values)
        migrate_engine.execute(update)

    # drop the columns that we don't need anymore
    revocation_event_table.c.issued_before.drop()
    revocation_event_table.c.expires_at.drop()
    revocation_event_table.c.revoked_at.drop()

    # rename the new column to the old names
    revocation_event_table.c.issued_before_int.alter(name='issued_before')
    revocation_event_table.c.expires_at_int.alter(name='expires_at')
    revocation_event_table.c.revoked_at_int.alter(name='revoked_at')
