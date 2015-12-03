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
    def derive_delegation(self, base_delegation,
                          agent, user, group, impersonation,
                          roles, project, domain,
                          strict_ancestry, sealed, executable):
        pass

    @abc.abstractmethod
    def update_delegation(self, delegation, grant_roles, revoke_roles):
        pass

    @abc.abstractmethod
    def revoke_delegation(self, delegation):
        pass

    @abc.abstractmethod
    def list_delegations(self, hints):
        pass

    @abc.abstractmethod
    def get_delegation(self, delegation):
        pass
