# Copyright 2017 SUSE Linux Gmbh
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


import json

from keystone.common import dependency
from keystone.common import driver_hints
from keystone.common import manager
import keystone.conf
from keystone import exception


CONF = keystone.conf.CONF

@dependency.provider('registered_limit_api')
class RegisteredLimitManager(manager.Manager):

    driver_namespace = 'keystone.registered_limit'

    def __init__(self):
        super(RegisteredLimitManager, self).__init__('sql')


    @manager.response_truncated
    def list_registered_limits(self, hints=None):
        return self.driver.list_registered_limits(
            hints or driver_hints.Hints())

    def get_registered_limit(
        self, service_type, region, resource_name):
        return self.driver.get_registered_limit(
            service_type, region, resource_name)

    def create_registered_limits(self, registered_limits):
        return [self.driver.create_registered_limit(registered_limit) for registered_limit in registered_limits]

    def update_registered_limits(self, registered_limits):
        return [self.driver.update_registered_limit(registered_limit) for registered_limit in registered_limits]

    def delete_registered_limit(self, service_type, region, resource_name):
        pass # not implemented


@dependency.provider('limit_api')
class LimitManager(manager.Manager):

    driver_namespace = 'keystone.limit'

    def __init__(self):
        super(LimitManager, self).__init__('sql')

    # TODO: @manager.response_truncated
    def list_limits(self, project_id, hints=None):
        return self.driver.list_limits(project_id, hints or driver_hints.Hints())

    def get_limit(self, project_id, service_type, region, resource_name):
        return self.driver.get_limit(
            project_id, service_type, region, resource_name)

    def create_or_update_limits(self, project_id, limits):
        ret_val = []
        for limit in limits:
            limit['project_id'] = project_id
            try:
                self.driver.get_limit(project_id,
                                      limit['service_type'],
                                      limit['region'],
                                      limit['resource_name'])
                ret_val.append(self.driver.update_limit(limit))
            except exception.LimitNotFound:
                ret_val.append(self.driver.create_limit(limit))
        return ret_val

    def delete_limits(self, project_id, service_type, region, resource_name):
        pass # not implemented
