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

import flask
from oslo_log import log
from oslo_policy import policy as common_policy
from oslo_utils import strutils

from keystone.common import authorization
from keystone.common import policies
from keystone.common import utils
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
    ACTION_STORE_ATTR = 'keystone:RBAC:action_name'

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

    @staticmethod
    def _build_filter_values(filters):
        """Extraxt fo;ter data from query params for RBAC enforcement."""
        filters = filters or []
        target = {i: flask.request.args[i] for
                  i in filters if i in flask.request.args}
        if target:
            if LOG.logger.getEffectiveLevel() <= log.DEBUG:
                LOG.debug(
                    'RBAC: Adding query filter params (%s)',
                    ', '.join(['%s=%s' % (k, v) for k, v in target.items()]))
        return target

    @staticmethod
    def _extract_member_target_data(member_target_type, member_target):
        """Build some useful target data.

        :param member_target_type: what type of target, e.g. 'user'
        :type member_target_type: str
        :param member_target: reference of the target data
        :type member_target: dict
        :returns: dict
        """
        ret_dict = {}
        if ((member_target is not None and member_target_type is None) or
                (member_target is None and member_target_type is not None)):
            LOG.warning('RBAC: Unknown target type or target reference. '
                        'Rejecting as unauthorized. '
                        '(member_target_type=%(target_type)r, '
                        'member_target=%(target_ref)r)',
                        {'member_target_type': member_target_type,
                         'target_ref': member_target})
            # Fast exit.
            return ret_dict

        if member_target is not None and member_target_type is not None:
            ret_dict['target'] = {member_target_type: member_target}
        else:
            # Try and do some magic loading based upon the resource we've
            # matched in our route. This is mostly so we can have a level of
            # automatic pulling in the resource; strictly for some added
            # DRY capabilities. In an ideal world the target is always passed
            # in explicitly.
            if flask.request.endpoint:
                # This only works for cases of Flask-RESTful
                resource_obj_class = flask.current_app.view_functions[
                    flask.request.endpoint].__class__
                member_name = getattr(resource_obj_class, 'member_name', None)
                func = getattr(
                    resource_obj_class, 'get_member_from_driver', None)
                if member_name is not None and func is not None:
                    key = '%s_id' % member_name
                    if key in (flask.request.view_args or {}):
                        ret_dict['target'] = {
                            member_name: func(flask.request.view_args[key])}
        return ret_dict

    @staticmethod
    def _extract_policy_check_credentials(action):
        # Pull out the auth context
        if LOG.logger.getEffectiveLevel() <= log.DEBUG:
            args_str = ', '.join(
                ['%s=%s' % (k, v) for
                 k, v in (flask.request.view_args or {}).items()])
            args_str = strutils.mask_password(args_str)
            LOG.debug('RBAC: Authorizing %(action)s(%(args)s)',
                      {'action': action, 'args': args_str})
        return flask.request.environ.get(authorization.AUTH_CONTEXT_ENV, {})

    @classmethod
    def enforce_call(cls, enforcer=None, action=None, target_attr=None,
                     member_target_type=None, member_target=None, *filters):
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
        :param target_attr: complete override of the target data. This will
                            replace all other generated target data meaning
                            `member_target_type` and `member_target` are
                            ignored. This will also prevent extraction of
                            data from the X-Subject-Token.
        :type target_attr: dict
        :param member_target_type: the type of the target, e.g. 'user'. Both
                                   this and `member_target` must be passed if
                                   either is passed.
        :type member_target_type: str
        :param member_target: the (dict form) reference of the member object.
                              Both this and `member_target_type` must be passed
                              if either is passed.
        :type member_target: dict
        :param filters: A variable number of optional positional parameter
                        string filters, these are used to extract values from
                        the query params. The filters are added to the request
                        data that is passed to the enforcer and may be used to
                        determine policy action. In practice these are mainly
                        supplied in the various "list" APIs and are un-used in
                        the default supplied policies.
        :type filters: str
        """
        # NOTE(morgan) everything in the policy_dict may be used by the policy
        # DSL to action on RBAC and request information/response data.
        policy_dict = {}

        # If "action" has not explicitly been overridden, see if it is set in
        # Flask.g app-context (per-request thread local) meaning the
        # @policy_enforcer_action decorator was used.
        action = action or getattr(flask.g, cls.ACTION_STORE_ATTR, None)
        if action not in _POSSIBLE_TARGET_ACTIONS:
            LOG.warning('RBAC: Unknown/No enforcement action name. Rejecting '
                        'as unauthorized, this is a programming error and a '
                        'bug should be filed with as much information about '
                        'the request that caused this as possible.')
            raise exception.Unauthorized(
                message=_(
                    'Internal RBAC enforcement error, no rule/action name to '
                    'lookup'))

        # Assert we are actually authenticated

        # TODO(morgan): make this work
        # assert_authenticated()

        # Check if "is_admin", this is in support of the old "admin auth token"
        # middleware with a shared "admin" token for auth

        # TODO(morgan): make this work
        # if is_admin:
        #     LOG.warning('RBAC: Bypassing authorization')
        #     return

        # NOTE(morgan): !!! ORDER OF THESE OPERATIONS IS IMPORTANT !!!
        # The lowest priority values are set first and the highest priority
        # values are set last.

        # Get the Target Data Set.
        if target_attr is not None:
            policy_dict.update(
                cls._extract_member_target_data(
                    member_target_type, member_target))

            # Special Case, extract and add subject_token data.
            # TODO(morgan): updte policy dict with data from subject token.
        else:
            policy_dict['target'] = target_attr

        # Pull the data from the view args (path based params) to generate
        # appropriate input/target attributes, we take an explicit copy here
        # to ensure we're not somehow corrupting
        policy_dict.update(flask.request.view_args or {})

        # Generate the filter_attr dataset.
        policy_dict.update(cls._build_filter_values(filters))

        # Extract the cred data
        creds = cls._extract_policy_check_credentials(action=action)

        # Instantiate the enforcer object if needed.
        enforcer_obj = enforcer or cls()
        enforcer_obj._enforce(creds, action, utils.flatten_dict(policy_dict))
        LOG.debug('RBAC: Authorization granted')

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
                setattr(flask.g, cls.ACTION_STORE_ATTR, action)
                return f(*args, **kwargs)
            return inner
        return wrapper

    @staticmethod
    def register_rules(enforcer):
        enforcer.register_defaults(policies.list_rules())
