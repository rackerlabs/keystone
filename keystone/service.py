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

import sys

import functools

import pecan

from keystone.api.common import hooks
from keystone.api.common import render
from keystone.api import root
from keystone.api import v2
from keystone.api import v3
from keystone import config
from keystone.openstack.common import log


CONF = config.CONF
LOG = log.getLogger(__name__)


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
    root.Controller.register_version('v2.0')
    return make_app(v2.PublicController())


@fail_gracefully
def admin_app_factory(global_conf, **local_conf):
    root.Controller.register_version('v2.0')
    return make_app(v2.AdminController())


@fail_gracefully
def public_version_app_factory(global_conf, **local_conf):
    return make_app(root.Controller('public'))


@fail_gracefully
def admin_version_app_factory(global_conf, **local_conf):
    return make_app(root.Controller('admin'))


@fail_gracefully
def v3_app_factory(global_conf, **local_conf):
    root.Controller.register_version('v3')
    return make_app(v3.Root())
