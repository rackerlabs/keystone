#!/usr/bin/env python
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

"""Runs the keystone admin and public servers using eventlet.

This module expects that the global config.CONF object has been configured
already, and that python logging has been configured.

"""

import logging
import signal
import socket
import sys

from paste import deploy

from keystone.common import environment
from keystone.common import utils
from keystone import config
from keystone.openstack.common import importutils
from keystone import service


CONF = config.CONF


def _create_server(conf, name, host, port):
    app = deploy.loadapp('config:%s' % conf, name=name)
    server = environment.Server(app, host=host, port=port)
    if CONF.ssl.enable:
        server.set_ssl(CONF.ssl.certfile, CONF.ssl.keyfile,
                       CONF.ssl.ca_certs, CONF.ssl.cert_required)
    return name, server


def _sigint_handler(signal, frame):
    """Exits at SIGINT signal."""
    logging.debug('SIGINT received, stopping servers.')
    sys.exit(0)


def _serve(*servers):
    signal.signal(signal.SIGINT, _sigint_handler)

    for name, server in servers:
        try:
            server.start()
        except socket.error:
            logging.exception(_('Failed to start the %(name)s server') % {
                'name': name})
            raise

    # notify calling process we are ready to serve
    if CONF.onready:
        try:
            notifier = importutils.import_module(CONF.onready)
            notifier.notify()
        except ImportError:
            try:
                utils.check_output(CONF.onready.split())
            except Exception:
                logging.exception('Failed to execute onready command')

    for name, server in servers:
        server.wait()


def run():

    # Log the options used when starting if we're in debug mode...
    if CONF.debug:
        CONF.log_opt_values(logging.getLogger(CONF.prog), logging.DEBUG)

    paste_config = config.find_paste_config()

    monkeypatch_thread = not CONF.standard_threads
    pydev_debug_url = utils.setup_remote_pydev_debug()
    if pydev_debug_url:
        # in order to work around errors caused by monkey patching we have to
        # set the thread to False.  An explanation is here:
        # http://lists.openstack.org/pipermail/openstack-dev/2012-August/
        # 000794.html
        monkeypatch_thread = False
    environment.use_eventlet(monkeypatch_thread)

    service.load_backends()

    servers = []
    servers.append(_create_server(paste_config,
                                  'admin',
                                  CONF.admin_bind_host,
                                  int(CONF.admin_port)))
    servers.append(_create_server(paste_config,
                                  'main',
                                  CONF.public_bind_host,
                                  int(CONF.public_port)))
    _serve(*servers)
