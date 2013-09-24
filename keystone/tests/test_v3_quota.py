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
