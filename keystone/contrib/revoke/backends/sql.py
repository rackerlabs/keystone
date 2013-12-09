# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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


import sqlalchemy

from keystone.common import sql
from keystone.contrib import revoke


class RevokedToken(sql.ModelBase, sql.DictBase):
    __tablename__ = 'revoked_token'
    attributes = ['id', 'scope_id', 'scope_type', 'valid_until',
                  'issued_at_or_after', 'issued_at_or_before',
                  'expires_at_or_after', 'expires_at_or_before']

    #index is not going to be exposed to the outside world.
    # It is, however,necessary for SQL Alchemy.  If we end up
    #sharing revocation IDs, we'll want them to be UUIDs
    id = sql.Column(sql.String(64), primary_key=True)
    scope_id = sql.Column(sql.String(64))
    scope_type = sql.Column(sqlalchemy.Integer())
    valid_until = sql.Column(sql.DateTime())
    issued_at_or_after = sql.Column(sql.DateTime())
    issued_at_or_before = sql.Column(sql.DateTime())
    expires_at_or_after = sql.Column(sql.DateTime())
    expires_at_or_before = sql.Column(sql.DateTime())

    #override base class which assumes class has "extra" attribute
    def __getitem__(self, key):
        return getattr(self, key)


class Revoke(sql.Base, revoke.Driver):
    def get_events(self, filter=None):
        """return the revocation events,

        :param filter:
        :raises: keystone.exception,
        :returns: None.

        """
        session = self.get_session()
        events = []
        query = session.query(RevokedToken).order_by(RevokedToken.scope_id)

        for e in query:
            kwargs = dict()
            for attr in e.attributes:
                kwargs[attr] = getattr(e, attr)
            events.append(revoke.RevokeEvent(**kwargs))
        return events

    def revoke(self, event):
        record = RevokedToken()

        for attr in record.attributes:
            record[attr] = getattr(event, attr)
        session = self.get_session()
        with session.begin():
            session.add(record)
