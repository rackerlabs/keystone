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

from oslo_policy import policy as common_policy

from keystone.common import policies
import keystone.conf
from keystone import exception


CONF = keystone.conf.CONF


_ENFORCER = None


def reset():
    global _ENFORCER
    _ENFORCER = None


def init():
    global _ENFORCER
    if not _ENFORCER:
        _ENFORCER = common_policy.Enforcer(CONF)
        register_rules(_ENFORCER)


def enforce(credentials, action, target, do_raise=True):
    """Verify that the action is valid on the target in this context.

    :param credentials: user credentials
    :param action: string representing the action to be checked, which should
                   be colon separated for clarity.
    :param target: dictionary representing the object of the action for object
                   creation this should be a dictionary representing the
                   location of the object e.g. {'project_id':
                   object.project_id}
    :raises keystone.exception.Forbidden: If verification fails.

    Actions should be colon separated for clarity. For example:

    * identity:list_users

    """
    init()

    # Add the exception arguments if asked to do a raise
    extra = {}
    if do_raise:
        extra.update(exc=exception.ForbiddenAction, action=action,
                     do_raise=do_raise)

    # NOTE(lbragstad): The configuration option here is what makes the behavior
    # backwards compatible. Once a deployment starts issues system role
    # assignments, they should be able to start enforcing system scope by
    # setting the configuration option to ``True``. At some point in the
    # future, we should considered changing the default from ``False`` to
    # ``True``, but for now this let's people fix RBAC in their deployment and
    # migrate to it while allowing for backwards compatibility.
    try:
        return _ENFORCER.enforce(
            action, target, credentials,
            enforce_scope=CONF.authorization.enforce_system_scope, **extra
        )
    except common_policy.InvalidScope as e:
        # NOTE(lbragstad): This means that the token used to make the request
        # wasn't scoped properly (e.g. using a project-scoped token to make a
        # system-level API call). We should handle this case and make sure
        # we're returning a 403 with details about why the request failed,
        # which the InvalidScope exception provides for us.
        raise exception.ForbiddenAction(e.message, action=action)


def register_rules(enforcer):
    enforcer.register_defaults(policies.list_rules())
