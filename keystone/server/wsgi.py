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

from oslo_config import cfg
import oslo_i18n


# NOTE(dstanek): i18n.enable_lazy() must be called before
# keystone.i18n._() is called to ensure it has the desired lazy lookup
# behavior. This includes cases, like keystone.exceptions, where
# keystone.i18n._() is called at import time.
oslo_i18n.enable_lazy()


from keystone.common import environment
from keystone.server import common


CONF = cfg.CONF


class WSGIApplication(common.AbstractApplication):

    def __init__(self, name, *args, **kwargs):
        super(WSGIApplication, self).__init__(*args, **kwargs)
        self.app_name = name
        self.wsgi_app = None

    def setup(self):
        # Log the options used when starting if we're in debug mode...
        if CONF.debug:
            CONF.log_opt_values(logging.getLogger(CONF.prog), logging.DEBUG)

        environment.use_stdlib()

    def startup_application(self):
        self.wsgi_app = self.get_wsgi_app(self.app_name)


def initialize_application(name):

    application = WSGIApplication(name)
    return application.wsgi_app
