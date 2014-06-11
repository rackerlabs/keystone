# Copyright 2014 IBM Corp.
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

import hashlib
import uuid

from keystone import config
from keystone import exception


CONF = config.CONF


class EntityType:
    USER = 'User'
    GROUP = 'Group'


def generate_public_ID(mapping):
    if CONF.identity_mapping.public_id_generator == 'uuid':
        return uuid.uuid4().hex

    if CONF.identity_mapping.public_id_generator == 'sha1':
        m = hashlib.sha1()
        m.update(mapping['domain_id'])
        m.update(mapping['local_id'])
        m.update(mapping['type'])
        return m.hexdigest()

    raise exception.UnsupportedMappingGenerator()
