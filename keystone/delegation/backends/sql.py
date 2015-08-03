# Copyright 2012 OpenStack Foundation
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


class DelegationModel(sql.DictBase):

    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'trustee_id',
                  'project_id',
                  'impersonation',
                  'origins',
                  'strict',
                  'deleted_at',
                  'expires_at',
                  'remaining_uses'
                  ]

    id = sql.Column(sql.String(64), primary_key=True)
    trustor_id = sql.Column(sql.String(64), nullable=False,)
    trustee_id = sql.Column(sql.String(64), nullable=False)
    project_id = sql.Column(sql.String(64))
    impersonation = sql.Column(sql.Boolean, nullable=False)
    origins = sql.Column(sql.Text)
    strict = sql.Column(sql.Boolean, nullable=False)

    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(sql.DateTime)
    remaining_uses = sql.Column(sql.Integer, nullable=True)


class RoleDelegationModel(sql.DictBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['delegation_id', 'role_id']

    delegation_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), nullable=False)

    __table_args__ = (sql.PrimaryKeyConstraint('delegation_id', 'role_id'), )
