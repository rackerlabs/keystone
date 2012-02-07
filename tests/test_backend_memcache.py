import uuid

from keystone import test
from tests import fakes
from keystone.token.backends import memcache as token_memcache


class MemcacheToken(test.TestCase):
    def setUp(self):
        super(MemcacheToken, self).setUp()
        fake_client = fakes.MemcacheClient()
        self.token_api = token_memcache.Token(client=fake_client)

    def test_token_crud(self):
        token_id = uuid.uuid4().hex
        data = {'id': token_id, 'a': 'b'}
        data_ref = self.token_api.create_token(token_id, data)
        self.assertDictEquals(data_ref, data)

        new_data_ref = self.token_api.get_token(token_id)
        self.assertEquals(new_data_ref, data)

        self.token_api.delete_token(token_id)
        deleted_data_ref = self.token_api.get_token(token_id)
        self.assertTrue(deleted_data_ref is None)
