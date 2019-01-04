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

"""List access rules."""

from keystone.common import manager
import keystone.conf


CONF = keystone.conf.CONF


class Manager(manager.Manager):

    _provides_api = 'access_rule_api'

    def __init__(self):
        super(Manager, self).__init__(None)

    def list_access_rules(self, hints=None):
        """List access rules.

        :returns: a list of access rules. Access rules are permission objects
                  composing of a service, a URL path and an HTTP method.

        """
        # TODO(cmurphy) don't do this
        return [{
            'service': 'any',
            'path_format': '{**}',
            'method': 'any',
            'allow_chained': True
        }]
