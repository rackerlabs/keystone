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

import functools

from flask import g
from oslo_log import log
from oslo_policy import policy as common_policy

from keystone.common import policies
import keystone.conf
from keystone import exception
from keystone.i18n import _


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


# SET Comprehension for possible action name(s)
_POSSIBLE_TARGET_ACTIONS = {rule.name for rule in policies.list_rules()}


class RBACEnforcer(object):
    """Enforce RBAC on API calls."""

    __shared_state__ = {}
    __ENFORCER = None
    ACTION_STORE_ATTR = 'keystone:rbac:action_name'

    def __init__(self):
        # NOTE(morgan): All Enforcer Instances use the same shared state;
        # BORG pattern.
        self.__dict__ = self.__shared_state__

    def _enforce(self, credentials, action, target, do_raise=True):
        """Verify that the action is valid on the target in this context.

        This method is for cases that exceed the base enforcer
        functionality (notably for compatibility with `@protected` style
        decorators.

        :param credentials: user credentials
        :param action: string representing the action to be checked, which
                       should be colon separated for clarity.
        :param target: dictionary representing the object of the action for
                       object creation this should be a dictionary
                       representing the location of the object e.g.
                       {'project_id': object.project_id}
        :raises keystone.exception.Forbidden: If verification fails.

        Actions should be colon separated for clarity. For example:

        * identity:list_users
        """
        # NOTE(morgan): Set the "app context" [per-request thread local]
        # value that indicates enforce has been called. This is only used by
        # the flask-native dispatched API calls.
        g.rbac_enforcement_called = True

        # Add the exception arguments if asked to do a raise
        extra = {}
        if do_raise:
            extra.update(exc=exception.ForbiddenAction, action=action,
                         do_raise=do_raise)

        try:
            return self._enforcer.enforce(action, target, credentials, **extra)
        except common_policy.InvalidScope:
            raise exception.ForbiddenAction(action=action)

    def _reset(self):
        # NOTE(morgan): Used for TEST purposes only.
        self.__ENFORCER = None

    @property
    def _enforcer(self):
        # The raw oslo-policy enforcer object
        if self.__ENFORCER is None:
            self.__ENFORCER = common_policy.Enforcer(CONF)
            self.register_rules(self.__ENFORCER)
        return self.__ENFORCER

    @classmethod
    def enforce_call(cls, enforcer=None, action=None):
        """Enforce RBAC on the current request.

        This will do some legwork and then instantiate the Enforcer if an
        enforcer is not passed in.

        :param enforcer: A pre-instantiated Enforcer object (optional)
        :type enforcer: :class:`RBACEnforcer`
        :param action: the name of the rule/policy enforcement to be checked
                       against, e.g. `identity:get_user` (optional may be
                       replaced by decorating the method/function with
                       `policy_enforcer_action`.
        :type action: str
        """
        # If "action" has not explicitly been overridden, see if it is set in
        # Flask.g app-context (per-request thread local) meaning the
        # @policy_enforcer_action decorator was used.
        action = action or getattr(g, cls.ACTION_STORE_ATTR, None)
        if action not in _POSSIBLE_TARGET_ACTIONS:
            LOG.warning('Unknown/No enforcement action name. Rejecting as '
                        'unauthorized, this is a programming error and a '
                        'bug should be filed with as much information about '
                        'the request that caused this as possible.')
            raise exception.Unauthorized(
                message=_(
                    'Internal RBAC enforcement error, no rule/action name to '
                    'lookup'))

    @classmethod
    def policy_enforcer_action(cls, action):
        """Decorator to set policy enforcement action name."""
        if action not in _POSSIBLE_TARGET_ACTIONS:
            raise ValueError('PROGRAMMING ERROR: Action must reference a '
                             'valid Keystone policy enforcement name.')

        def wrapper(f):
            @functools.wraps(f)
            def inner(*args, **kwargs):
                # Set the action in g on a known attr so we can reference it
                # later.
                setattr(g, cls.ACTION_STORE_ATTR, action)
                return f(*args, **kwargs)
            return inner
        return wrapper

    @staticmethod
    def register_rules(enforcer):
        enforcer.register_defaults(policies.list_rules())
