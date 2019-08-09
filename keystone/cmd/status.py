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

from oslo_upgradecheck import upgradecheck

from keystone.common import provider_api
import keystone.conf
from keystone.server import backends

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class Checks(upgradecheck.UpgradeCommands):
    """Programmable upgrade checks.

    Each method here should be a programmable check that helps check for things
    that might cause issues for deployers in the upgrade process. A good
    example of an upgrade check would be to ensure all roles defined in
    policies actually exist within the roles backend.
    """

    def check_default_roles_are_immutable(self):
        roles = PROVIDERS.role_api.list_roles()
        default_roles = ('admin', 'member', 'reader',)
        failed_roles = []
        for role in [r for r in roles if r['name'] in default_roles]:
            if not role.get('options', {}).get('immutable'):
                failed_roles.append(role['name'])
        if any(failed_roles):
            return upgradecheck.Result(
                upgradecheck.Code.FAILURE,
                "Roles are not immutable: %s" % ", ".join(failed_roles)
            )
        return upgradecheck.Result(
            upgradecheck.Code.SUCCESS, "Default roles are immutable.")

    _upgrade_checks = (
        ("Check default roles are immutable",
         check_default_roles_are_immutable),
    )


def main():
    keystone.conf.configure()
    backends.load_backends()
    return upgradecheck.main(CONF, 'keystone', Checks())
