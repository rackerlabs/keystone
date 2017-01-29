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

from oslo_log import log
import six

from keystone.auth import controllers
from keystone.common import dependency
import keystone.conf
from keystone.i18n import _, _LI, _LE
from keystone.identity.backends import resource_options as ro


LOG = log.getLogger(__name__)

CONF = keystone.conf.CONF


@dependency.requires('identity_api')
class UserMFARulesValidator(object):
    """Helper object that can validate the MFA Rules."""

    @property
    def _auth_methods(self):
        if controllers.AUTH_PLUGINS_LOADED:
            return set(controllers.AUTH_METHODS.keys())
        raise RuntimeError(_('Auth Method Plugins are not loaded.'))

    def check_auth_methods_against_rules(self, user_id, auth_methods):
        """Validate the MFA rules against the successful auth methods.

        :param user_id: The user's ID (uuid).
        :type user_id: str
        :param auth_methods: List of methods that were used for auth
        :type auth_methods: set
        :returns: Boolean, ``True`` means rules match and auth may proceed,
                  ``False`` means rules do not match.
        """
        user_ref = self.identity_api.get_user(user_id)
        mfa_rules = user_ref['options'].get(ro.MFA_RULES_OPT.option_name, [])
        mfa_rules_enabled = user_ref['options'].get(
            ro.MFA_ENABLED_OPT.option_name, True)
        rules = self._parse_rule_structure(mfa_rules, user_ref['id'])

        if not rules or not mfa_rules_enabled:
            # return quickly if the rules are disabled for the user or not set
            LOG.debug('User MFA Rules not processed for %(user_id)s. '
                      'Rule list: %(rules)r (Enabled: %(enabled)s).',
                      {'user_id': user_id,
                       'rules': mfa_rules,
                       'enabled': mfa_rules_enabled})
            return True

        for r in rules:
            # NOTE(notmorgan): We only check against the actually loaded
            # auth methods meaning that the keystone administrator may
            # disable an auth method, and a rule will still pass making it
            # impossible to accidently lock-out a subset of users with a
            # bad keystone.conf
            r_set = r.intersection(self.auth_methods)
            if auth_methods.issuperset(set(r_set)):
                # Rule Matches no need to continue, return here.
                LOG.debug('User %(user_id)s auth methods %(methods)r '
                          'matched MFA rule %(rule)r. Loaded '
                          'auth_methods: %(loaded)s',
                          {'user_id': user_id,
                           'rule': r_set,
                           'loaded': self._auth_methods})
                return True

        LOG.debug('User %(user_id)s auth methods %(methods)r did not match a '
                  'MFA rule in %(rules)r.',
                  {'user_id': user_id,
                   'methods': auth_methods,
                   'rules': rules})
        return False

    @staticmethod
    def _parse_rule_structure(rules, user_id):
        """Validate and parse the rule data structure.

        Rule sets must be in the form of list of lists. The lists may not
        have duplicates and must not be empty. The top-level list may be empty
        indicating that no rules exist.

        :param rules: The list of rules from the user_ref
        :type rules: list
        :param user_id: the user_id, used for logging purposes
        :type user_id: str
        :returns: set of sets ensuring no duplicated rules.
        """
        # NOTE(notmorgan): Most of this is done at the API request validation
        # and in the storage layer, it makes sense to also validate here and
        # ensure the data returned from the DB is sane, This will not raise
        # any exceptions, but just produce a usable set of data for rules
        # processing.
        rule_set = set()
        if not isinstance(rules, list):
            LOG.error(_LE('Corrupt rule data structure for user %(user_id)s, '
                          'no rules loaded.'),
                      {'user_id': user_id})
            return rule_set
        elif not rules:
            return rule_set

        for r_list in rules:
            if not isinstance(r_list, list):
                LOG.info(_LI('Ignoring Rule %(rule)r; rule must be a list of '
                             'strings.'),
                         {'type': type(r_list)})
                continue

            if r_list:
                # No empty rules are allowed.
                for item in r_list:
                    if not isinstance(item, six.string_types):
                        # Rules may only contain strings for method names
                        # Reject a rule with non-string values
                        LOG.info(_LI('Ignoring Rule %(rule)r; rule contains '
                                     'non-string values.'),
                                 {'rule': r_list})
                    else:
                        # NOTE(notmorgan): Use of sets here ensures no
                        # duplicate rules and no duplicate elements in the
                        # rules.
                        rule_set.add(set(r_list))

        return rule_set
