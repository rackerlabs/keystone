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

class RevokedToken(sql.ModelBase, sql.DictBase):
    __tablename__ = 'revoked_token'
    attributes = ['scope_id', 'scope_type','expires_net', 'expires_nlt']
    
    scope_id = sql.Column(sql.String(64)),
    scope_type = sql.Column(sql.Integer()),
    expires_net = sql.Column( sql.DateTime()),
    expires_nlt = sql.Column( sql.DateTime()),
