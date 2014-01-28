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


import datetime

from keystone.common import config
from keystone.common import sql
from keystone.contrib import revoke
from keystone.contrib.revoke import model

from keystone.openstack.common.db.sqlalchemy import session as db_session
from keystone.openstack.common import timeutils


CONF = config.CONF


class RevocationEvent(sql.ModelBase, sql.DictBase):
    __tablename__ = 'revocation_event'
    attributes = model.revoke_keys

    #index is not going to be exposed to the outside world.
    # It is, however,necessary for SQL Alchemy.  If we end up
    #sharing revocation IDs, we'll want them to be UUIDs
    id = sql.Column(sql.String(64), primary_key=True)
    domain_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    user_id = sql.Column(sql.String(64))
    role_id = sql.Column(sql.String(64))
    trust_id = sql.Column(sql.String(64))
    consumer_id = sql.Column(sql.String(64))
    access_token_id = sql.Column(sql.String(64))
    issued_before = sql.Column(sql.DateTime())
    expires_at = sql.Column(sql.DateTime())
    revoked_at = sql.Column(sql.DateTime())

    #override base class which assumes class has "extra" attribute
    def __getitem__(self, key):
        return getattr(self, key)

    #override to avoid dealing with the 'extra' field
    def to_dict(self, include_extra_dict=False):
        d = dict()
        for attr in self.__class__.attributes:
            d[attr] = getattr(self, attr)

        return d


class Revoke(sql.Base, revoke.Driver):
    def _flush_batch_size(self, dialect):
        batch_size = 0
        if dialect == 'ibm_db_sa':
            # This functionality is limited to DB2, because
            # it is necessary to prevent the tranaction log
            # from filling up, whereas at least some of the
            # other supported databases do not support update
            # queries with LIMIT subqueries nor do they appear
            # to require the use of such queries when deleting
            # large numbers of records at once.
            batch_size = 100
            # Limit of 100 is known to not fill a transaction log
            # of default maximum size while not significantly
            # impacting the performance of large token purges on
            # systems where the maximum transaction log size has
            # been increased beyond the default.
        return batch_size

    def _prune_expired_events(self):
        #add 30 minutes to token expiration to make sure that we don't have
        #issues with clock skew.  In practice, 5 minutes should be enough.
        oldest = revoke.revoked_before_cutoff()

        session = db_session.get_session()
        dialect = session.bind.dialect.name
        batch_size = self._flush_batch_size(dialect)
        if batch_size > 0:
            query = session.query(RevocationEvent.id)
            query = query.filter(RevocationEvent.revoked_at < oldest)
            query = query.limit(batch_size).subquery()
            delete_query = (session.query(RevocationEvent).
                            filter(RevocationEvent.id.in_(query)))
            while True:
                rowcount = delete_query.delete(synchronize_session=False)
                if rowcount == 0:
                    break
        else:
            query = session.query(RevocationEvent)
            query = query.filter(RevocationEvent.revoked_at < oldest)
            query.delete(synchronize_session=False)

        session.flush()

    def get_events(self, last_fetch=None):
        """return the revocation events,

        :param filter:
        :raises: keystone.exception,
        :returns: None.

        """
        self._prune_expired_events()
        session = db_session.get_session()
        query = session.query(RevocationEvent).order_by(
            RevocationEvent.revoked_at)

        #this should be filtered by revokend_at, but it is broken
        #Maybe SQLite?
        if last_fetch:
            query.filter(RevocationEvent.revoked_at > last_fetch)
            events = []
            for e in query:
                if last_fetch and e.revoked_at > last_fetch:
                    events.append(model.RevokeEvent(**e.to_dict(False)))
        else:
            events = [model.RevokeEvent(**e.to_dict(False)) for e in query]
        return events

    def revoke(self, event):
        kwargs = dict()
        for attr in model.revoke_keys:
            kwargs[attr] = getattr(event, attr)
        kwargs['id'] = str(kwargs['id'])
        record = RevocationEvent(**kwargs)

        session = db_session.get_session()
        with session.begin():
            session.add(record)
