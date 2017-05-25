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

# Placeholders for microversions
_MIN_API_VERSION = "3.0"
_MAX_API_VERSION = "3.8"
_DEPRECATED_API_VERSION = "2.0"


def min_api_version():
    version = _MIN_API_VERSION
    status = 'stable'
    updated = '2017-02-22T00:00:00Z'
    return {"version": version, "status": status, "updated": updated}


def max_api_version():
    version = _MAX_API_VERSION
    status = 'stable'
    updated = '2017-02-22T00:00:00Z'
    return {"version": version, "status": status, "updated": updated}


def deprecated_api_version():
    version = _DEPRECATED_API_VERSION
    status = 'deprecated'
    updated = '2016-08-04T00:00:00Z'
    return {"version": version, "status": status, "updated": updated}
