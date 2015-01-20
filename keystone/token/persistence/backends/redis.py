# Copyright 2012 OpenStack Foundation
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

"""
Keystone Redis dogpile.cache backend implementation.
"""

from keystone.common import config
from keystone.token.persistence.backends import kvs


CONF = config.CONF


class Token(kvs.Token):
    kvs_backend = 'dogpile.cache.redis'

    def __init__(self, *args, **kwargs):
        super(Token, self).__init__(*args, **kwargs)
