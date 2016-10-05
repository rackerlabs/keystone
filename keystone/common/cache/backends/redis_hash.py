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

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE
from dogpile.cache.backends import redis
import pickle
from dogpile.cache import register_backend


class RedisHashBackend(redis.RedisBackend):

    def __init__(self, arguments):
        super(RedisHashBackend, self).__init__(arguments)
        self.hash_name = arguments.pop('hash_name')

    def get_mutex(self, key):
        if self.distributed_lock:
            return self.client.lock(
                '_lock{0}_{1}'.format(self.hash_name, key),
                self.lock_timeout, self.lock_sleep)
        else:
            return None

    def get(self, key):
        value = self.client.hget(self.hash_name, key)
        if value is None:
            return NO_VALUE
        return pickle.loads(value)

    def get_multi(self, keys):
        if not keys:
            return []
        values = self.client.hmget(self.hash_name, keys)
        return [
            pickle.loads(v) if v is not None else NO_VALUE
            for v in values]

    def set(self, key, value):
        self.client.hset(
            self.hash_name, key, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))

    def set_multi(self, mapping):
        mapping = dict(
            (k, pickle.dumps(v, pickle.HIGHEST_PROTOCOL))
            for k, v in mapping.items()
        )

        if not self.redis_expiration_time:
            self.client.hmset(self.hash_name, mapping)

    def delete(self, key):
        self.client.hdel(self.hash_name, key)

    def delete_multi(self, keys):
        self.client.hdel(self.hash_name, *keys)


register_backend("redis_hash", __name__, "RedisHashBackend")

region = make_region().configure(
    'redis_hash',
    arguments={
        'hash_name': 'myhash'
    }
)
