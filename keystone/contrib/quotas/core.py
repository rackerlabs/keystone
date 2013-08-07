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

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager


extension.register_admin_extension(
    'OS-QUOTAS', {
        'name': 'OpenStack Keystone Quotas',
        'namespace': 'http://docs.openstack.org/identity/api/ext/'
                     'OS-QUOTAS/v1.0',
        'alias': 'OS-QUOTAS',
        'updated': '2013-07-11T17:14:00-00:00',
        'description': 'OpenStack extensions to Keystone v3.0 API '
                       'enabling Administrative Operations.',
        'links': [
            {
                'rel': 'describedby',
                'type': 'text/html',
                'href': 'https://github.com/openstack/identity-api',
            }
        ]})


@dependency.provider('quotas_api')
class Manager(manager.Manager):

    def __init__(self):
        super(Manager, self).__init__(
            'keystone.contrib.quotas.backends.sql.SQLQuotaDriver')
