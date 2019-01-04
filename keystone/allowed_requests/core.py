# Copyright 2019 SUSE Linux GmbH
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

"""List allowed request strings."""

from keystone.common import manager
import keystone.conf


CONF = keystone.conf.CONF


class Manager(manager.Manager):

    _provides_api = 'allowed_request_api'

    def __init__(self):
        super(Manager, self).__init__(None)

    def list_allowed_requests(self, hints=None):
        """List allowed request formats.

        :returns: a list of HTTP requests against an OpenStack service that an
                  application credential is allowed to make

        """
        return [{
            'service': 'any',
            'path_format': '{**}',
            'method': 'any'
        }]
