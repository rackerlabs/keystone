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

from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF
LOG = log.getLogger(__name__)


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
    def list_delegations(self, hints, user, group, project, domain,
                         expanded=False):
        pass

    @abc.abstractmethod
    def get_delegation(self, delegation_id):
        pass
