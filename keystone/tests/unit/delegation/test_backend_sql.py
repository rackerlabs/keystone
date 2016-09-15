# Copyright 2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from oslo_context import context as oslo_context

from keystone.tests import unit
from keystone.tests.unit import test_v3_assignment
from keystone.tests.unit import test_v3_auth
from keystone.tests.unit import test_v3_oauth1


class DelegationAssignmentTestCase(test_v3_assignment.AssignmentTestCase):

    def config_overrides(self):
        super(DelegationAssignmentTestCase, self).config_overrides()
        self.config_fixture.config(
            group='assignment',
            driver='keystone.delegation.backends.sql.AssignmentDriver')

    def load_sample_data(self):
        domain = unit.new_domain_ref()
        domain_id = domain['id']
        self.resource_api.create_domain(domain_id, domain)
        user = unit.create_user(self.identity_api,
                                domain_id=domain_id)
        context = oslo_context.get_current()
        context.user = user['id']
        super(DelegationAssignmentTestCase, self).load_sample_data()


class DelegationTrustTestCase(test_v3_auth.TrustAPIBehavior,
                              test_v3_auth.TestTrustChain):

    def config_overrides(self):
        super(DelegationTrustTestCase, self).config_overrides()
        self.config_fixture.config(
            group='trust',
            driver='keystone.delegation.backends.sql.TrustDriver')


class DelegationOAuth1UUIDTestCase(test_v3_oauth1.UUIDAuthTokenTests):

    def config_overrides(self):
        super(DelegationOAuth1UUIDTestCase, self).config_overrides()
        self.config_fixture.config(
            group='oauth1',
            driver='keystone.delegation.backends.sql.OAuth1Driver')


class DelegationOAuth1FernetTestCase(test_v3_oauth1.FernetAuthTokenTests):

    def config_overrides(self):
        super(DelegationOAuth1FernetTestCase, self).config_overrides()
        self.config_fixture.config(
            group='oauth1',
            driver='keystone.delegation.backends.sql.OAuth1Driver')
