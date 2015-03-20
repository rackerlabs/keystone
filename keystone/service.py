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

import functools
import sys

from oslo_config import cfg
from oslo_log import log
from paste import deploy
import pecan

from keystone.api.common import hooks
from keystone.api.common import render
from keystone.api import root
from keystone import controllers


CONF = cfg.CONF
LOG = log.getLogger(__name__)


def loadapp(conf, name):
    # NOTE(blk-u): Save the application being loaded in the controllers module.
    # This is similar to how public_app_factory() and v3_app_factory()
    # register the version with the controllers module.
    controllers.latest_app = deploy.loadapp(conf, name=name)
    return controllers.latest_app


def fail_gracefully(f):
    """Logs exceptions and aborts."""
    @functools.wraps(f)
    def wrapper(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            LOG.debug(e, exc_info=True)

            # exception message is printed to all logs
            LOG.critical(e)
            sys.exit(1)

    return wrapper


def make_app(controller, **kwargs):
    # NOTE(jamielennox): Reset global pecan config. Works around some strange
    # edge cases with running two pecan apps in the same namespace in testing.
    pecan.set_config({'app': {}}, overwrite=True)

    kwargs['custom_renderers'] = {'keystone': render.KeystoneRenderer}
    kwargs.setdefault('hooks', []).append(hooks.ProcessHook())
    return pecan.make_app(controller, **kwargs)


@fail_gracefully
def public_app_factory(global_conf, **local_conf):
    root.register_version('v2.0')
    return make_app('keystone.api.v2.PublicRootController')


@fail_gracefully
def admin_app_factory(global_conf, **local_conf):
    root.register_version('v2.0')
    return make_app('keystone.api.v2.AdminRootController')


@fail_gracefully
def public_version_app_factory(global_conf, **local_conf):
    return make_app('keystone.api.root.PublicRootController')


@fail_gracefully
def admin_version_app_factory(global_conf, **local_conf):
    return make_app('keystone.api.root.AdminRootController')


@fail_gracefully
def v3_app_factory(global_conf, **local_conf):
    root.register_version('v3')
    return make_app('keystone.api.v3.RootController')
