# Copyright 2016 Morgan Fainberg
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


class UUIDMsgPackModel(sql.ModelBase):
    __tablename__ = 'token_uuid_msgpack'
    attributes = ['id', 'creation_time', 'expires_time', 'payload']
    id = sql.Column(sql.Integer(40), primary_key=True)
    creation_time = sql.Column(sql.DateTime(), default=None, nullable=None)
    payload = sql.Column(sql.String(255), default=None, nullable=False)
    __table_args__ = (
        sql.Index('ix_token_create_time', 'creation_time')
    )
