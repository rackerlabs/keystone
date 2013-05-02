# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

import os
import subprocess
import time
import logging

from keystone import config
from keystone import test
from keystone.common import utils
from keystone.common import wsgi

import default_fixtures

CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id
OPENSTACK_REPO = 'https://review.openstack.org/p/openstack'
KEYSTONECLIENT_REPO = '%s/python-keystoneclient.git' % OPENSTACK_REPO
LOG = logging.getLogger(__name__)

cd = os.chdir


def checkout_vendor(repo, rev):
    # TODO(termie): this function is a good target for some optimizations :PERF
    name = repo.split('/')[-1]
    if name.endswith('.git'):
        name = name[:-4]

    working_dir = os.getcwd()
    revdir = os.path.join(test.VENDOR, '%s-%s' % (name, rev.replace('/', '_')))
    modcheck = os.path.join(test.VENDOR, '.%s-%s' %
                            (name, rev.replace('/', '_')))
    try:
        if os.path.exists(modcheck):
            mtime = os.stat(modcheck).st_mtime
            if int(time.time()) - mtime < 10000:
                return revdir

        if not os.path.exists(revdir):
            utils.git('clone', repo, revdir)

        cd(revdir)
        utils.git('checkout', '-q', 'master')
        utils.git('pull', '-q')
        utils.git('checkout', '-q', rev)

        # write out a modified time
        with open(modcheck, 'w') as fd:
            fd.write('1')
    except subprocess.CalledProcessError:
        LOG.warning(_('Failed to checkout %s'), repo)
    cd(working_dir)
    return revdir


class CompatTestCase(test.TestCase):
    def setUp(self):
        super(CompatTestCase, self).setUp()

        revdir = checkout_vendor(*self.get_checkout())

        self.load_backends()
        self.load_fixtures(default_fixtures)

        # TODO(termie): is_admin is being deprecated once the policy stuff
        #               is all working
        # TODO(termie): add an admin user to the fixtures and use that user
        # override the fixtures, for now
        self.metadata_foobar = self.identity_api.update_metadata(
            self.user_foo['id'], self.tenant_bar['id'],
            dict(roles=[self.role_admin['id']], is_admin='1'))

        self.public_server = self.serveapp('keystone', name='main')
        self.admin_server = self.serveapp('keystone', name='admin')

        self.add_path(revdir)
        self.clear_module('keystoneclient')

    def serveapp(self, config, name=None, cert=None, key=None, ca=None,
                 cert_required=None, host="127.0.0.1", port=0):
        app = self.loadapp(config, name=name)
        server = wsgi.Server(app, host, port)
        if cert is not None and ca is not None and key is not None:
            server.set_ssl(certfile=cert, keyfile=key, ca_certs=ca,
                           cert_required=cert_required)
        server.start(key='socket')

        # Service catalog tests need to know the port we ran on.
        port = server.socket_info['socket'][1]
        self.opt(public_port=port, admin_port=port)
        return server

    def tearDown(self):
        self.public_server.kill()
        self.admin_server.kill()
        self.public_server = None
        self.admin_server = None
        super(CompatTestCase, self).tearDown()

    def _public_url(self):
        public_port = self.public_server.socket_info['socket'][1]
        return "http://localhost:%s/v2.0" % public_port

    def _admin_url(self):
        admin_port = self.admin_server.socket_info['socket'][1]
        return "http://localhost:%s/v2.0" % admin_port

    def _client(self, admin=False, **kwargs):
        from keystoneclient.v2_0 import client as ks_client

        url = self._admin_url() if admin else self._public_url()
        kc = ks_client.Client(endpoint=url,
                              auth_url=self._public_url(),
                              **kwargs)
        kc.authenticate()
        # have to manually overwrite the management url after authentication
        kc.management_url = url
        return kc

    def get_client(self, user_ref=None, tenant_ref=None, admin=False):
        if user_ref is None:
            user_ref = self.user_foo
        if tenant_ref is None:
            for user in default_fixtures.USERS:
                if user['id'] == user_ref['id']:
                    tenant_id = user['tenants'][0]
        else:
            tenant_id = tenant_ref['id']

        return self._client(username=user_ref['name'],
                            password=user_ref['password'],
                            tenant_id=tenant_id,
                            admin=admin)
