# Copyright 2015 Mirantis Inc
# All Rights Reserved.
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

from dogpile.cache.backends import redis as dogpile_redis_backend

from oslo_config import cfg

CONF = cfg.CONF


class RedisBackend(dogpile_redis_backend.RedisBackend):
    """Dogpile cache backend using Redis with secure password usage

    Backend is configured using following parameters passed in [cache] section:

    :param redis_url: string. If provided will override separate host/port/db
        params.
         The format is that accepted by ``StrictRedis.from_url()``,
         for example:

    - redis://[:password]@localhost:6379/0
    - unix://[:password]@/path/to/socket.sock?db=0

    ``cache.backend_argument``:

    :param redis_host: string, default is ``localhost``.
    :param redis_password: string, default is no password.
    :param redis_port: integer, default is ``6379``.
    :param redis_db: integer, default is ``0``.

    Advanced parameters can be passed via ``cache.backend_argument``:

    :param redis_expiration_time: integer, number of seconds after setting a
         value that Redis should expire it.  This should be larger than
         dogpile's cache expiration. By default no expiration is set.
    :param distributed_lock: boolean, when True, will use a
         redis-lock as the dogpile lock.
         Use this when multiple
         processes will be talking to the same redis instance.
         When left at False, dogpile will coordinate on a regular
         threading mutex.
    :param lock_timeout: integer, number of seconds after acquiring a lock that
         Redis should expire it.  This argument is only valid when
         ``distributed_lock`` is ``True``.
    :param socket_timeout: float, seconds for socket timeout.
         Default is None (no timeout).

    :param lock_sleep: integer, number of seconds to sleep when failed to
         acquire a lock.  This argument is only valid when
         ``distributed_lock`` is ``True``.
    """

    def __init__(self, arguments):
        kwargs = dict(arguments)
        kwargs['url'] = CONF.cache.redis_url
        kwargs['host'] = CONF.cache.redis_host
        kwargs['port'] = CONF.cache.redis_port
        kwargs['password'] = CONF.cache.redis_password
        kwargs['db'] = CONF.cache.redis_db
        super(RedisBackend, self).__init__(kwargs)