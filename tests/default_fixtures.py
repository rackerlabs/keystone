# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

TENANTS = [
    {'id': 'bar', 'name': 'BAR'},
    {'id': 'baz', 'name': 'BAZ'},
    {'id': 'tenent4add', 'name': 'tenant4add'},
    ]

# NOTE(ja): a role of keystone_admin and attribute "is_admin" is done in setUp
USERS = [
    {'id': 'foo', 'name': 'FOO', 'password': 'foo2', 'tenants': ['bar']},
    {'id': 'two', 'name': 'TWO', 'password': 'two2', 'tenants': ['baz']},
    {'id': 'no_meta',
     'name': 'NO_META',
     'password': 'no_meta2',
     'tenants': ['baz']},
    ]

METADATA = [
    {'user_id': 'foo', 'tenant_id': 'bar', 'extra': 'extra'},
    {'user_id': 'two', 'tenant_id': 'baz', 'extra': 'extra'},
    ]

ROLES = [
    {'id': 'keystone_admin', 'name': 'Keystone Admin'},
    {'id': 'useless', 'name': 'Useless'},
    ]

SERVICES = [
    {
        'id': 'COMPUTE_ID',
        'type': 'compute',
        'name': 'Nova',
        'description': 'OpenStack Compute service'
    },
    {
        'id': 'IDENTITY_ID',
        'type': 'identity',
        'name': 'Keystone',
        'description': 'OpenStack Identity service'
    },
    {
        'id': 'IMAGE_ID',
        'type': 'image',
        'name': 'Glance',
        'description': 'OpenStack Image service'
    },
]

ENDPOINTS = [
    {
        'id': 'COMPUTE_IMAGE_ID',
        'region': 'RegionOne',
        'service_id': 'IMAGE_ID',
        'adminurl': 'http://localhost:9292/v1',
        'internalurl': 'http://localhost:9292/v1',
        'publicurl': 'http://localhost:9292/v1'
    },
    {
        'id': 'COMPUTE_ENDPOINT_ID',
        'region': 'RegionOne',
        'service_id': 'COMPUTE_ID',
        'adminurl': 'http://localhost:$(compute_port)s/v1.1/$(tenant_id)s',
        'internalurl': 'http://localhost:$(compute_port)s/v1.1/$(tenant_id)s',
        'publicurl': 'http://localhost:$(compute_port)s/v1.1/$(tenant_id)s'
    },
    {
        'id': 'IDENTITY_ENDPOINT_ID',
        'region': 'RegionOne',
        'service_id': 'IDENTITY_ID',
        'adminurl': 'http://localhost:$(admin_port)s/v2.0',
        'internalurl': 'http://localhost:$(public_port)s/v2.0',
        'publicurl': 'http://localhost:$(public_port)s/v2.0'
    },
]
