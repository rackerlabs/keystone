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

from keystone.common import sql
from keystone.common.sql import migration
from keystone import exception


class Message(sql.ModelBase, sql.DictBase):
    """Example message table."""
    __tablename__ = 'example'
    attributes = ['id', 'type', 'extra']
    msg_id = sql.Column(sql.String(64),
                            primary_key=True,
                            nullable=False)
    msg_type = sql.Column(sql.String(255))
    msg_time = sql.Column(sql.Text()))


class Example(sql.Base):
    # Internal interface to manage the database

    def db_sync(self, version=None):
        migration.db_sync(version=version)

    def add_message(self, message_id, message_type, timestamp):
        session = self.get_session()
        with session.begin():
            message_ref = Message(msg_id=message_id,
                                  msg_type=message_type,
                                  msg_extra=timestamp)
            session.add(message_ref)
            session.flush()

    def _get_message_ref(self, session, message_id):
        message_ref = session.query(Message).get((message_id))
        if message_ref is None:
            msg = _('Message %(message_id)s not found in example'
                    % {'message_id': message_id}
            raise exception.NotFound(msg)
        return message_ref

    def remove_message(self, message_id):
        session = self.get_session()
        message_ref = self._get_message_ref(session, message_id)
        with session.begin():
            session.delete(message_ref)
            session.flush()
