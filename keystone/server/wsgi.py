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

from oslo import i18n
from paste import deploy


# NOTE(dstanek): i18n.enable_lazy() must be called before
# keystone.i18n._() is called to ensure it has the desired lazy lookup
# behavior. This includes cases, like keystone.exceptions, where
# keystone.i18n._() is called at import time.
i18n.enable_lazy()


from keystone.common import environment
from keystone import config
from keystone.server import common


CONF = config.CONF


def initialize_application(name):
    common.configure()
    environment.use_stdlib()

    def loadapp():
        return deploy.loadapp('config:%s' % config.find_paste_config(),
                              name=name)

    _unused, application = common.setup_backends(loadapp)
    return application
