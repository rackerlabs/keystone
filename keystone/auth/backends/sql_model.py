# Copyright 2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
from keystone.common import sql


class FailedAuthAttempts(sql.ModelBase, sql.DictBase):
    __tablename__ = 'failed_auth_attempts'
    attributes = ['id', 'user_id', 'timestamp']

    # id = sql.Column(sql.String(64), primary_key=True)
    id = sql.Column(sql.Integer, primary_key=True)
    user_id = sql.Column(sql.String(64), index=True)
    timestamp = sql.Column(sql.DateTime())
    extra = sql.Column(sql.JsonBlob())
