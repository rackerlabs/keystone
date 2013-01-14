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

# NOTE(dolph): please try to avoid additional fixtures if possible; test suite
#              performance may be negatively affected.

PROJECTS = [
    {
        'id': 'bar',
        'name': 'BAR',
    }, {
        'id': 'baz',
        'name': 'BAZ',
        'description': 'description',
        'enabled': True,
    }
]

# NOTE(ja): a role of keystone_admin and attribute "is_admin" is done in setUp
USERS = [
    {
        'id': 'foo',
        'name': 'FOO',
        'password': 'foo2',
        'projects': ['bar']
    }, {
        'id': 'two',
        'name': 'TWO',
        'password': 'two2',
        'email': 'two@example.com',
        'enabled': True,
        'project_id': 'baz',
        'projects': ['baz'],
    }, {
        'id': 'badguy',
        'name': 'BadGuy',
        'password': 'bad',
        'email': 'bad@guy.com',
        'enabled': False,
        'project_id': 'baz',
        'projects': ['baz'],
    }
]

METADATA = [
#    {
#        'user_id': 'foo',
#        'project_id': 'bar',
#        'extra': 'extra',
#    }
]

ROLES = [
    {
        'id': 'keystone_admin',
        'name': 'Keystone Admin',
    }, {
        'id': 'member',
        'name': 'Member',
    }
]
