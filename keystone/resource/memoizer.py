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

from keystone.common import cache
from keystone.common import dependency
from keystone.common import memoizer
from keystone import resource


MEMOIZE = cache.get_memoization_decorator(group='resource')

@dependency.provider('resource_api')
class Memoizer(memoizer.Memoizer):

    def __init__(self):
        self.manager = resource.Manager(self)

    @MEMOIZE
    def get_project(self, project_id):
        return self.manager.get_project(project_id)

    @MEMOIZE
    def get_project_by_name(self, tenant_name, domain_id):
        return self.manager.get_project_by_name(tenant_name, domain_id)

    def create_project(self, project_id, project, initiator=None):
        ret = self.manager.create_project(project_id, project, initiator)
        if MEMOIZE.should_cache(ret):
            self.get_project.set(ret, self, project_id)
            self.get_project_by_name.set(ret, self, ret['name'],
                                         ret['domain_id'])
        return ret

    @MEMOIZE
    def get_domain(self, domain_id):
        return self.manager.get_domain(domain_id)

    @MEMOIZE
    def get_domain_by_name(self, domain_name):
        return self.manager.get_domain_by_name(domain_name)

    def update_domain(self, domain_id, domain, initiator=None):
        ret = self.manager.update_domain(domain_id, domain, initiator)
        self.get_domain.invalidate(self, domain_id)
        # TODO(samueldmq): should use original domain from driver
        #self.get_domain_by_name.invalidate(self, domain['name'])
        return ret

    def delete_domain(self, domain_id, initiator=None):
        self.manager.delete_domain(domain_id, initiator)
        self.get_domain.invalidate(self, domain_id)
        # TODO(samueldmq): uncomment below
        # self.get_domain_by_name.invalidate(self, domain['name'])

    def create_domain(self, domain_id, domain, initiator=None):
        ret = self.manager.create_domain(domain_id, domain, initiator=None)

        if MEMOIZE.should_cache(ret):
            self.get_domain.set(ret, self, domain_id)
            self.get_domain_by_name.set(ret, self, ret['name'])

        return ret

    def update_project(self, project_id, project, initiator=None):
        ret = self.manager.update_project(project_id, project, initiator)
        self.get_project.invalidate(self, project_id)
        # TODO(samueldmq): should use original project from driver
        #self.get_project_by_name.invalidate(self, project['name'],
        #                                    project['domain_id'])
        return ret

    def delete_project(self, project_id, initiator=None):
        ret = self.manager.delete_project(project_id, initiator)
        self.get_project.invalidate(self, project_id)
        # TODO(samueldmq): uncomment below
        #self.get_project_by_name.invalidate(self, ret['name'],
        #                                    ret['domain_id'])
        return ret
