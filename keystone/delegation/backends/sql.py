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

from datetime import datetime
import uuid

from keystone.common import sql
from keystone import config

CONF = config.CONF


class DelegationModel(sql.DictBase):
    """Unified delegation model

      'trustor_id': the user considered the source of delegated rights
      'impersonation': allowance for the delegate to impersonate the trustor
      'origins': ancestry chain of delegations
      'ancestors': ancestry chain of trustors
      'strict': whether to check if trustors are all enabled
      'transitive': indicates that rights can be delegated further
      'active': delegated rights can be used by the delegate
      'user_id': delegate user id empowered by the delegation
      'group_id': delegate group id which users are empowered by the delegation
      'project_id': scope of the delegation - the object of rights passed
      'domain_id': scope of the delegation - the object of rights passed
      'deleted_at': timestamp of delegation revocation
      'expires_at': timestamp of delegation expiration
      'remaining_uses': RESERVED
    """
    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'impersonation',
                  'origins',
                  'ancestors',
                  'strict',
                  'transitive',
                  'active',
                  'user_id',
                  'group_id',
                  'project_id',
                  'domain_id',
                  'deleted_at',
                  'expires_at',
                  'remaining_uses'
                  ]

    DELIMITER = '.'

    id = sql.Column(sql.String(64), primary_key=True,
                    default=lambda: uuid.uuid4().hex)

    # Identification
    trustor_id = sql.Column(sql.String(64), nullable=False)
    impersonation = sql.Column(sql.Boolean, nullable=False, default=False)
    origins = sql.Column(sql.Text, nullable=False, default='')
    ancestors = sql.Column(sql.Text, nullable=False, default='')

    # Constraints
    strict = sql.Column(sql.Boolean, nullable=False, default=False)
    transitive = sql.Column(sql.Boolean, nullable=False, default=False)
    active = sql.Column(sql.Boolean, nullable=False, default=False)

    # Scope
    user_id = sql.Column(sql.String(64))
    group_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    domain_id = sql.Column(sql.String(64))
    inherited = sql.Column(sql.Boolean, default=False, nullable=False)

    # Timestamps
    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(
        sql.DateTime, default=lambda:
        datetime.now() + CONF.delegation.expiration)

    # Specific fields, may be moved to "extra" blob
    remaining_uses = sql.Column(sql.Integer)

    def inherit(self, agent_id, strict):
        inherited = type(self)()
        inherited.trustor_id = self.trustor_id
        inherited.origins = self.DELIMITER.join(
            self.origins.split(self.DELIMITER) + [self.id])
        inherited.ancestors = self.DELIMITER.join(
            self.ancestors.split(self.DELIMITER) + [agent_id])
        inherited.strict = strict

        return inherited

    def scope(self, user_id=None, group_id=None, impersonation=False,
              project_id=None, domain_id=None, inherited=False):
        # TODO(amakarov): XOR user, group
        self.user_id = user_id
        self.group_id = group_id
        self.impersonation = impersonation

        # TODO(amakarov): XOR project, domain
        self.project_id = project_id
        self.domain_id = domain_id
        self.inherited = inherited

        return self


class RoleDelegationModel(sql.DictBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['delegation_id', 'role_id']

    delegation_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), nullable=False)

    __table_args__ = (sql.PrimaryKeyConstraint('delegation_id', 'role_id'), )
