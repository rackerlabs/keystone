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

import test_v3


class DomainQuotaTestCase(test_v3.RestfulTestCase):
    """Test domain quotas RUD."""

    def setUp(self):
        super(DomainQuotaTestCase, self).setUp()

    def test_get_quota_domain_defaults(self):
        self.put('/domains/%s/quotas' % self.domain_id,
                 body={'quotas': {'region': 'USA', 'nova': {'instances': 27}}},
                 expected_status=200)

        self.get("/domains/%s/quotas" % self.domain_id,
                 body={"quotas": {"region": "USA", "services": ["nova"]}},
                 expected_status=200)

    def test_get_quota_domain_nonexistent(self):
        self.get("/domains/233/quotas",
                 body={"quotas": {"region": "USA", "services": ["nova"]}},
                 expected_status=404)

    def test_get_quota_domain_no_region(self):
        self.get("/domains/%s/quotas" % self.domain_id,
                 body={"quotas": {"services": ["nova"]}},
                 expected_status=400)

    def test_get_quota_domain_no_services(self):
        self.get("/domains/%s/quotas" % self.domain_id,
                 body={"quotas": {"region": "USA"}},
                 expected_status=400)

    def test_delete_domain_quota(self):
        self.put('/domains/%s/quotas' % self.domain_id,
                 body={'quotas': {'region': 'USA', 'nova': {'instances': 27}}},
                 expected_status=200)

        self.delete('/domains/%s/quotas' % self.domain_id,
                    body={"quotas": {"region": "USA", "services": ["nova"]}},
                    expected_status=200)

    def test_delete_quota_domain_nonexistent(self):
        self.delete("/domains/233/quotas",
                    body={"quotas": {"region": "USA", "services": ["nova"]}},
                    expected_status=404)

    def test_delete_domain_quota_no_region(self):
        self.delete("/domains/%s/quotas" % self.domain_id,
                    body={"quotas": {"services": ["nova"]}},
                    expected_status=400)

    def test_delete_domain_quota_no_services(self):
        self.delete("/domains/%s/quotas" % self.domain_id,
                    body={'quotas': {'region': 'USA'}},
                    expected_status=400)

    def test_update_domain_quota(self):
        self.put('/domains/%s/quotas' % self.domain_id,
                 body={'quotas': {'region': 'USA', 'nova': {'instances': 27}}},
                 expected_status=200)
        self.put('/domains/%s/quotas' % self.domain_id,
                 body={'quotas': {'region': 'USA', 'nova': {'instances': 14}}},
                 expected_status=200)

    def test_update_domain_quota_domain_nonexistent(self):
        self.put('/domains/233/quotas',
                 body={'quotas': {'region': 'USA', 'nova': {'instances': 20}}},
                 expected_status=404)

    def test_update_domain_quota_domain_no_region(self):
        self.put('/domains/%s/quotas' % self.domain_id,
                 body={'quotas': {'nova': {'instances': 20}}},
                 expected_status=400)
