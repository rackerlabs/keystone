# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import logging

from keystone.application import common
from keystone.common import environment
from keystone import config
from keystone.openstack.common import log
from keystone import service


CONF = config.CONF

LOG = log.getLogger(__name__)


def create_application(name):

    environment.use_stdlib()

    if CONF.debug:
        CONF.log_opt_values(log.getLogger(CONF.prog), logging.DEBUG)

    service.load_backends()

    paste_config = config.find_paste_config()

    app = common.loadapp('config:%s' % paste_config, name=name)

    return app
