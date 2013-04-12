# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

import nose.exc

from keystone.common import sql
from keystone.common import uid
from keystone import config
from keystone import test

import test_keystoneclient


CONF = config.CONF


class KcMasterSqlTestCase(test_keystoneclient.KcMasterTestCase):
    def config(self, config_files):
        super(KcMasterSqlTestCase, self).config([
            test.etcdir('keystone.conf.sample'),
            test.testsdir('test_overrides.conf'),
            test.testsdir('backend_sql.conf')])

    def tearDown(self):
        sql.set_global_engine(None)
        super(KcMasterSqlTestCase, self).tearDown()

    def test_endpoint_crud(self):
        from keystoneclient import exceptions as client_exceptions

        client = self.get_client(admin=True)

        service = client.services.create(name=uid.new(),
                                         service_type=uid.new(),
                                         description=uid.new())

        endpoint_region = uid.new()
        invalid_service_id = uid.new()
        endpoint_publicurl = uid.new()
        endpoint_internalurl = uid.new()
        endpoint_adminurl = uid.new()

        # a non-existent service ID should trigger a 404
        self.assertRaises(client_exceptions.NotFound,
                          client.endpoints.create,
                          region=endpoint_region,
                          service_id=invalid_service_id,
                          publicurl=endpoint_publicurl,
                          adminurl=endpoint_adminurl,
                          internalurl=endpoint_internalurl)

        endpoint = client.endpoints.create(region=endpoint_region,
                                           service_id=service.id,
                                           publicurl=endpoint_publicurl,
                                           adminurl=endpoint_adminurl,
                                           internalurl=endpoint_internalurl)

        self.assertEquals(endpoint.region, endpoint_region)
        self.assertEquals(endpoint.service_id, service.id)
        self.assertEquals(endpoint.publicurl, endpoint_publicurl)
        self.assertEquals(endpoint.internalurl, endpoint_internalurl)
        self.assertEquals(endpoint.adminurl, endpoint_adminurl)

        client.endpoints.delete(id=endpoint.id)
        self.assertRaises(client_exceptions.NotFound, client.endpoints.delete,
                          id=endpoint.id)

    def test_endpoint_create_404(self):
        from keystoneclient import exceptions as client_exceptions
        client = self.get_client(admin=True)
        self.assertRaises(client_exceptions.NotFound,
                          client.endpoints.create,
                          region=uid.new(),
                          service_id=uid.new(),
                          publicurl=uid.new(),
                          adminurl=uid.new(),
                          internalurl=uid.new())

    def test_endpoint_delete_404(self):
        from keystoneclient import exceptions as client_exceptions
        client = self.get_client(admin=True)
        self.assertRaises(client_exceptions.NotFound,
                          client.endpoints.delete,
                          id=uid.new())

    def test_policy_crud(self):
        # FIXME(dolph): this test was written prior to the v3 implementation of
        #               the client and essentially refers to a non-existent
        #               policy manager in the v2 client. this test needs to be
        #               moved to a test suite running against the v3 api
        raise nose.exc.SkipTest('Written prior to v3 client; needs refactor')

        from keystoneclient import exceptions as client_exceptions
        client = self.get_client(admin=True)

        policy_blob = uid.new()
        policy_type = uid.new()
        service = client.services.create(
            name=uid.new(),
            service_type=uid.new(),
            description=uid.new())
        endpoint = client.endpoints.create(
            service_id=service.id,
            region=uid.new(),
            adminurl=uid.new(),
            internalurl=uid.new(),
            publicurl=uid.new())

        # create
        policy = client.policies.create(
            blob=policy_blob,
            type=policy_type,
            endpoint=endpoint.id)
        self.assertEquals(policy_blob, policy.policy)
        self.assertEquals(policy_type, policy.type)
        self.assertEquals(endpoint.id, policy.endpoint_id)

        policy = client.policies.get(policy=policy.id)
        self.assertEquals(policy_blob, policy.policy)
        self.assertEquals(policy_type, policy.type)
        self.assertEquals(endpoint.id, policy.endpoint_id)

        endpoints = [x for x in client.endpoints.list() if x.id == endpoint.id]
        endpoint = endpoints[0]
        self.assertEquals(policy_blob, policy.policy)
        self.assertEquals(policy_type, policy.type)
        self.assertEquals(endpoint.id, policy.endpoint_id)

        # update
        policy_blob = uid.new()
        policy_type = uid.new()
        endpoint = client.endpoints.create(
            service_id=service.id,
            region=uid.new(),
            adminurl=uid.new(),
            internalurl=uid.new(),
            publicurl=uid.new())

        policy = client.policies.update(
            policy=policy.id,
            blob=policy_blob,
            type=policy_type,
            endpoint=endpoint.id)

        policy = client.policies.get(policy=policy.id)
        self.assertEquals(policy_blob, policy.policy)
        self.assertEquals(policy_type, policy.type)
        self.assertEquals(endpoint.id, policy.endpoint_id)

        # delete
        client.policies.delete(policy=policy.id)
        self.assertRaises(
            client_exceptions.NotFound,
            client.policies.get,
            policy=policy.id)
        policies = [x for x in client.policies.list() if x.id == policy.id]
        self.assertEquals(len(policies), 0)
