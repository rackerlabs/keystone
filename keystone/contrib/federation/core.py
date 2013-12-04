# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

"""Extension supporting Clouds Federation."""

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import config
from keystone.openstack.common import log as logging

CONF = config.CONF
LOG = logging.getLogger(__name__)
#NOTE(marek-denis): fill with 100% proper data.
EXTENSION_DATA = {
    'name': 'OpenStack virtual Identity Providers API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-IDP/v1.0',
    'alias': 'OS-IDP',
    #NOTE(marek-denis): copy/paste
    'updated': '2013-07-07T12:00:0-00:00',
    'description': 'OpenStack virtual Identity Providers Mechanism.',
    'links': [
            {
            'rel': 'describedby',
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api'
            }
    ]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)
extension.register_public_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


@dependency.provider('federation_api')
class Manager(manager.Manager):
    """Default pivot point for the Federation backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """
    def __init__(self):
        super(Manager, self).__init__(CONF.federation.driver)
