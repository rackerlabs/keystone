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

import os

from keystoneclient.openstack.common.apiclient import exceptions
from keystoneclient.v3 import client


OS_SERVICE_URL = (os.environ.get('OS_SERVICE_URL') or
                  'http://localhost:35357/v3/')
OS_PROJECT_NAME = os.environ.get('OS_PROJECT_NAME') or 'admin'


def create_or_find(entity_manager, **kwargs):
    possible_id_attrs = ['id', 'name', 'mapping_id']
    try:
        entity = entity_manager.create(**kwargs)
    except exceptions.Conflict:
        for attr in possible_id_attrs:
            if attr in kwargs:
                entity = entity_manager.find(**{attr: kwargs[attr]})
                break
        else:
            raise Exception('no attr?')
    return entity


ks = client.Client(endpoint=OS_SERVICE_URL,
                   token='password',
                   project_name='admin')


domain = create_or_find(ks.domains, name='pysaml2-d')
group = create_or_find(ks.groups, name='pysaml2-g', domain=domain)
role = create_or_find(ks.roles, name='pysaml2-user')
ks.roles.grant(role=role, group=group, domain=domain)

#
# federation setup
#

rules = [
    {
        "local": [
            {
                "user": {"name": "{0}"}
            },
            {
                "group": {"id": group.id}
            }
        ],
        "remote": [
            {
                "type": "openstack_user",
                "any_one_of": [
                    "user1",
                    "admin"
                ]
            }
        ]
    }
]

idp = create_or_find(ks.federation.identity_providers, id='pysaml2-idp')
mapping = create_or_find(ks.federation.mappings,
                         mapping_id='pysaml2-mapping',
                         rules=rules)
protocol = create_or_find(ks.federation.protocols,
                          protocol_id='saml2',
                          identity_provider=idp,
                          mapping=mapping)
