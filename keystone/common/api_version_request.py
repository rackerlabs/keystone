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

    * 1.0 Depricated
    * 2.0 Depricated
    * 3.0 Current: No microversions yet

"""

# Placeholders for microversions
_MIN_API_VERSION = "3.0"
_MAX_API_VERSION = "3.0"
_LEGACY_API_VERSION1 = "1.0"
_LEGACY_API_VERSION2 = "2.0"


def min_api_version():
    return APIVersionRequest(_MIN_API_VERSION)


def max_api_version():
    return APIVersionRequest(_MAX_API_VERSION)


def legacy_api_version1():
    return APIVersionRequest(_LEGACY_API_VERSION1)


def legacy_api_version2():
    return APIVersionRequest(_LEGACY_API_VERSION2)


class APIVersionRequest(object):
    """This class represents an API Version Request.

    This class includes convenience methods for manipulation
    and comparison of version numbers as needed to implement
    API microversions.
    """

    def get_version(self, version_string):
        status = None
        if 'v3' in version_string:
            status = "Current: v3 Identity API"
        elif 'v2' in version_string:
            status = "Depricated: v2 Identity API"
        elif 'v1' in version_string:
            status = "Depricated: v1 Identity API"

        return status
