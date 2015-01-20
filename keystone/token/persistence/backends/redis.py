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

"""
Keystone Redis dogpile.cache token storage implementation.

To use this backend set in the [token] section of config file:

.. code::

    driver=keystone.token.persistence.backends.redis.Token

Backend is configured using parameters passed in ``cache.backend_argument``:

:param url: string. If provided, will override separate host/port/db params.
The format is that accepted by ``StrictRedis.from_url()``, for example:

- redis://[:password]@localhost:6379/0
- unix://[:password]@/path/to/socket.sock?db=0

:param host: string, default is ``localhost``.
:param password: string, default is no password.
:param port: integer, default is ``6379``.
:param db: integer, default is ``0``.
:param redis_expiration_time: integer, number of seconds after setting a value
     that Redis should expire it.  This should be larger than dogpile's cache
     expiration. By default no expiration is set.
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

:param connection_pool: ``redis.ConnectionPool`` object.  If provided,
     this object supersedes other connection arguments passed to the
     ``redis.StrictRedis`` instance, including url and/or host as well as
     socket_timeout, and will be passed to ``redis.StrictRedis`` as the
     source of connectivity.

"""

from keystone.token.persistence.backends import kvs


class Token(kvs.Token):
    kvs_backend = 'dogpile.cache.redis'

    def __init__(self, *args, **kwargs):
        super(Token, self).__init__(*args, **kwargs)
