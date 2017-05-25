# Copyright 2017 AT&T Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

REST_API_VERSION_HISTORY = """

    REST API Version History:

    * 2.0 Deprecated
    * 3.0 Current: v3.8

"""


class VersionFactory(object):

    _min_api_version = '3.0'
    _max_api_version = '3.8'
    _deprecated_api_version = '2.0'

    @property
    def deprecated_api_version(self):
        return self._deprecated_api_version

    @property
    def max_api_version(self):
        return self._max_api_version

    @property
    def min_api_version(self):
        return self._min_api_version

    def stability(self, version):
        if version == self.deprecated_api_version:
            status = 'deprecated'
        else:
            status = 'stable'
        return status

    def last_updated(self, version):
        if version == self.deprecated_api_version:
            last_updated = '2016-08-04T00:00:00Z'
        else:
            last_updated = '2017-02-22T00:00:00Z'
        return last_updated
