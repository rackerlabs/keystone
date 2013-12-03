# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Deutsche Telekom AG
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

import logging

from keystone.openstack.common import threadgroup
from keystone import config
from keystone import token


LOG = logging.getLogger(__name__)
CONF = config.CONF


class PeriodicTasks(object):
    def __init__(self):
        #add periodic tasks
        if CONF.token.flush_period > 0:
            self.__tg = threadgroup.ThreadGroup()
            self.__tg.add_timer(CONF.token.flush_period,
                                self.__task_flush_expired_tokens,
                                initial_delay=CONF.token.flush_period)
            LOG.debug("flush expired tokens periodically every {0} seconds"
                      .format(CONF.token.flush_period))

    def __task_flush_expired_tokens(self):
        """periodically flush the expired tokens"""
        token_manager = token.Manager()
        token_manager.driver.flush_expired_tokens()
        LOG.debug("periodic flush of expired tokens done")
