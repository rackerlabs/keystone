# Copyright 2014 Mirantis Inc.
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

""" Sample of plugin.

For more keystone related benchmarks take a look here:
github.com/stackforge/rally/blob/master/rally/benchmark/scenarios/keystone/

About plugins: https://rally.readthedocs.org/en/latest/plugins.html

Rally concepts https://wiki.openstack.org/wiki/Rally/Concepts
"""


from rally.benchmark.scenarios import base
from rally.benchmark.scenarios import utils as scenario_utils


class KeystonePlugin(base.Scenario):

    @scenario_utils.atomic_action_timer("create_user_label")
    def _create_user(self, name_length=10):
        name = self._generate_random_name(length=name_length)
        password = name
        email = name + "@example.com"
        return self.admin_clients("keystone").users.create(name, password,
                                                           email)

    @scenario_utils.atomic_action_timer("delete_user_label")
    def _delete_user(self, user):
        user.delete()

    @base.scenario(admin_only=True)
    def create_and_delete_user(self, name_length=10):
        user = self._create_user(name_length)
        self._delete_user(user)
