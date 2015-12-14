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

import abc
import six

from keystone.common import dependency
from keystone.common import manager
from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class BaseManager(manager.Manager):
    """Base for default pivot point for the Delegation backend.

    See :class:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.delegation'

    def __init__(self):
        delegation_driver = CONF.delegation.driver
        super(BaseManager, self).__init__(delegation_driver)

    def validate_delegation(self, delegation):
        pass


@dependency.provider('delegation_api')
class Manager(manager.Manager):
    """Base for default pivot point for the Delegation backend.

    See :class:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """


@six.add_metaclass(abc.ABCMeta)
class DelegationDriverV8(object):
    """Driver interface for delegation low level management"""

    @abc.abstractmethod
    def derive_delegation(self, id, base_delegation,
                          agent, user, group, impersonation,
                          roles, project, domain, inherited_to_projects,
                          strict_ancestry, sealed, executable, expires_at):
        pass

    @abc.abstractmethod
    def update_delegation(self, delegation, grant_roles, revoke_roles):
        pass

    @abc.abstractmethod
    def revoke_delegation(self, delegation):
        pass

    @abc.abstractmethod
    def list_delegations(self, hints=None, user=None, group=None,
                         project=None, domain=None, role=None,
                         expanded=False):
        pass

    @abc.abstractmethod
    def get_delegation(self, delegation):
        pass


class TrustManager(BaseManager):
    """Trust interface manager using delegation."""

    @staticmethod
    def _to_trust(delegation_ref):
        trust_ref = {
            'id': delegation_ref['id'],
            'trustor_user_id': delegation_ref['trustor_id'],
            'trustee_user_id': delegation_ref['user_chain'][-1],
            'project_id': delegation_ref['project_id'],
            'impersonation': delegation_ref['impersonation'],
            'expires_at': delegation_ref['expires_at'],
            'remaining_uses': delegation_ref['remaining_uses'],
            'deleted_at': delegation_ref['deleted_at'],
            'redelegated_trust_id': delegation_ref['delegation_chain'][-1],
            'redelegation_count': CONF.trust.max_redelegation_count,
            'roles': delegation_ref['roles']
        }
        return trust_ref

    @staticmethod
    def _from_trust_no_ancestry(trust_ref, roles):
        ref = {
            'id': trust_ref['id'],
            'trustor_id': trust_ref['trustor_user_id'],
            'project_id': trust_ref['project_id'],
            'impersonation': trust_ref['impersonation'],
            'expires_at': trust_ref['expires_at'],
            'deleted_at': trust_ref['deleted_at'],
            'roles': trust_ref.get('roles', roles)
        }
        return ref

    def get_trust(self, trust_id, deleted=False):
        delegation_ref = self.driver.get_delegation(delegation=trust_id)
        self.validate_delegation(delegation_ref)
        return self._to_trust(delegation_ref)

    def create_trust(self, trust_id, trust, roles, redelegated_trust=None,
                     initiator=None):
        if redelegated_trust:
            base_delegation = self.driver.get_trust(redelegated_trust['id'])
        else:
            base_delegation = None
        self.driver.derive_delegation(
            id=trust_id,
            base_delegation=base_delegation,
            agent=trust['trustor_user_id'],
            user=trust['trustee_user_id'],
            group=None,
            impersonation=trust['impersonation'],
            roles=roles,
            project=trust['project_id'],
            domain=None,
            inherited_to_projects=False,
            strict_ancestry=True,
            executable=True,
            sealed=trust.get('allow_redelegation', False))

    def delete_trust(self, trust_id, initiator=None):
        self.driver.revoke_delegation(delegation=trust_id)
