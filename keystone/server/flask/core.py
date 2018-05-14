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

import collections
import os

import oslo_i18n
from oslo_log import log
import stevedore


# NOTE(dstanek): i18n.enable_lazy() must be called before
# keystone.i18n._() is called to ensure it has the desired lazy lookup
# behavior. This includes cases, like keystone.exceptions, where
# keystone.i18n._() is called at import time.
oslo_i18n.enable_lazy()

from keystone.common import profiler
import keystone.conf
from keystone.server import common
from keystone.server.flask import application

# NOTE(morgan): Middleware Named Tuple with the following values:
#   * "namespace": namespace for the entry_point
#   * "ep": the entry-point name
#   * "config": extra config data for the entry_point (None or Dict)
_Middleware = collections.namedtuple('LoadableMiddleware',
                                     'namespace, ep')


CONF = keystone.conf.CONF
# NOTE(morgan): ORDER HERE IS IMPORTANT! The middleware will process the
# request in this list's order.
_APP_MIDDLEWARE = (
    _Middleware(namespace='keystone.server_middleware', ep='healthcheck'),
    _Middleware(namespace='keystone.server_middleware', ep='cors'),
    _Middleware(namespace='keystone.server_middleware', ep='sizelimit'),
    _Middleware(
        namespace='keystone.server_middleware', ep='http_proxy_to_wsgi'),
    _Middleware(namespace='keystone.server_middleware', ep='osprofiler'),
    _Middleware(namespace='keystone.server_middleware', ep='request_id'),
    _Middleware(
        namespace='keystone.server_middleware', ep='build_auth_context'),
    _Middleware(namespace='keystone.server_middleware', ep='token_auth'),
    _Middleware(namespace='keystone.server_middleware', ep='json_body'),
    _Middleware(namespace='keystone.server_middleware', ep='url_normalize'),
)


def _get_config_files(env=None):
    if env is None:
        env = os.environ

    dirname = env.get('OS_KEYSTONE_CONFIG_DIR', '').strip()

    files = [s.strip() for s in
             env.get('OS_KEYSTONE_CONFIG_FILES', '').split(';') if s.strip()]

    if dirname:
        if not files:
            files = ['keystone.conf']
        files = [os.path.join(dirname, fname) for fname in files]

    return files


def setup_app_middleware(application):
    # NOTE(morgan): Load the middleware, in reverse order, we wrap the app
    # explicitly; reverse order to ensure the first element in _APP_MIDDLEWARE
    # processes the request first.

    # TODO(morgan): Add mechanism to allow for externally loaded middleware
    # at the end of the middleware-stack via config.

    for mw in reversed(_APP_MIDDLEWARE):
        # Load via Stevedore, initialize the class via the factory so we can
        # initialize the "loaded" entrypoint with the currently bound
        # object pointed at "application". We may need to eventually move away
        # from the "factory" mechanism.
        loaded = stevedore.DriverManager(
            mw.namespace, mw.ep, invoke_on_load=False)
        loaded_mw = loaded.driver(CONF)
        application = loaded_mw(application)
    return application


def initialize_application(name, post_log_configured_function=lambda: None,
                           config_files=None):
    possible_topdir = os.path.normpath(os.path.join(
                                       os.path.abspath(__file__),
                                       os.pardir,
                                       os.pardir,
                                       os.pardir))

    dev_conf = os.path.join(possible_topdir,
                            'etc',
                            'keystone.conf')
    if not config_files:
        config_files = None
        if os.path.exists(dev_conf):
            config_files = [dev_conf]

    common.configure(config_files=config_files)

    # Log the options used when starting if we're in debug mode...
    if CONF.debug:
        CONF.log_opt_values(log.getLogger(CONF.prog), log.DEBUG)

    post_log_configured_function()

    # TODO(morgan): Provide a better mechanism than "loadapp", this was for
    # paste-deploy specific mechanisms.
    def loadapp():
        app = application.application_factory(name)
        return app

    _unused, app = common.setup_backends(
        startup_application_fn=loadapp)

    # setup OSprofiler notifier and enable the profiling if that is configured
    # in Keystone configuration file.
    profiler.setup(name)

    return setup_app_middleware(app)
