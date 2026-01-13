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

from keystone.common import provider_api
from keystone import exception

PROVIDERS = provider_api.ProviderAPIs


def validate_project_access(user_id, project_id):
    roles = PROVIDERS.assignment_api.get_roles_for_user_and_project(
        user_id, project_id
    )
    if not roles:
        # Match missing-project responses without confirming project existence.
        raise exception.ProjectNotFound(project_id=project_id)
