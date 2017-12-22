#!/bin/bash

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

export KSTEST_ADMIN_URL=http://keystone.openstack:80
export KSTEST_PUBLIC_URL=http://keystone.openstack:80
export KSTEST_ADMIN_USERNAME='admin'
export KSTEST_ADMIN_PASSWORD='password'
export KSTEST_ADMIN_DOMAIN_ID='default'

export KSTEST_USER_USERNAME='admin'
export KSTEST_USER_PASSWORD='password'
export KSTEST_USER_DOMAIN_ID='default'

export KSTEST_PROJECT_NAME='admin'

tox -e functional

curl -i   -H "Content-Type: application/json" -d \
  '{ "auth": {
    "identity": {
      "methods": ["password"],
      "password": {
        "user": {
          "name": "admin",
          "domain": { "id": "default" },
          "password": "password"
        }
      }
    },
    "scope": {
      "project": {
        "name": "admin",
        "domain": { "id": "default" }
      }
    }
  }
}' "http://keystone.openstack:80/v3/auth/tokens" ; echo
