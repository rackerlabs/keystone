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
import os

from oslo import i18n
from paste import deploy


# NOTE(dstanek): i18n.enable_lazy() must be called before
# keystone.i18n._() is called to ensure it has the desired lazy lookup
# behavior. This includes cases, like keystone.exceptions, where
# keystone.i18n._() is called at import time.
i18n.enable_lazy()


from keystone import backends
from keystone.common import dependency
from keystone.common import environment
from keystone.common import sql
from keystone.common import utils
from keystone import config
from keystone.openstack.common import log


CONF = config.CONF

config.configure()
sql.initialize()
config.set_default_for_default_log_levels()

CONF(project='keystone')
config.setup_logging()
LOG = log.getLogger(__name__)

environment.use_stdlib()
name = os.path.basename(__file__)



if CONF.debug:
    CONF.log_opt_values(log.getLogger(CONF.prog), logging.DEBUG)

if CONF.remote_debug == os.path.basename(__file__):
    LOG.debug('remote_debugging should be enabled:')
    LOG.debug('this file is :%s:' % os.path.basename(__file__))
    LOG.debug('debugger set for:%s:' % CONF.remote_debug)
    LOG.debug('remote_debugging_host:%s' % CONF.remote_debug_host)
    LOG.debug('remote_debugging_port:%s' % CONF.remote_debug_port)
    try:
        utils.setup_remote_pydev_debug()
        LOG.debug('debugging beginning')
    except Exception as e:
        LOG.exception(e)




drivers = backends.load_backends()

# NOTE(ldbragst): 'application' is required in this context by WSGI spec.
# The following is a reference to Python Paste Deploy documentation
# http://pythonpaste.org/deploy/
application = deploy.loadapp('config:%s' % config.find_paste_config(),
                             name=name)

dependency.resolve_future_dependencies()
