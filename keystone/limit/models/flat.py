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

from keystone.limit.models import base


class Model(base.ModelBase):

    NAME = 'flat'
    DESCRIPTION = (
        'Limit enforcement and validation does not take project hierarchy '
        'into consideration.'
    )
    MAX_PROJECT_TREE_DEPTH = None

    def check_limit_hierarchy_creating(self, limits):
        # Flat limit model is not hierarchical, so don't need to check the
        # value.
        return

    def check_limit_hierarchy_updating(self, limit_id, limit):
        # Flat limit model is not hierarchical, so don't need to check the
        # value.
        return

    def get_project_ids_tree(self, project_id):
        # Flat limit model doesn't support hierarchy. So return None here even
        # though the specified project is in a hierarchy project tree.
        return
