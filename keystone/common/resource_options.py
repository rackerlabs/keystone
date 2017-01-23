# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Options specific to resources managed by Keystone (Domain, User, etc)."""

import six

from keystone.i18n import _


def _validator(value):
    return


class ResourceOptionRegistry(object):
    def __init__(self, registry_name):
        self._registered_options = {}
        self._registry_type = registry_name

    @property
    def option_names(self):
        return set([opt.option_name for opt in self.options])

    @property
    def options(self):
        return self._registered_options.values()

    @property
    def option_ids(self):
        return set(self._registered_options.keys())

    def get_option_by_fourcc(self, fourcc):
        return self._registered_options.get(fourcc, None)

    def get_option_by_name(self, name):
        for option in self._registered_options.values():
            if name == option.option_name:
                return option
        return None

    def _clear_registered_options(self):
        """For testing purposes, this clears all registered options."""
        self._registered_options.clear()

    def register_option(self, option):
        if option in self.options:
            # Re-registering the exact same option does nothing.
            return

        if option.option_id in self._registered_options:
            raise ValueError(_('Option %(option_id)s already defined in '
                               '%(registry)s.') %
                             {'option_id': option.option_id,
                              'registry': self._registry_type})
        if option.option_name in self.option_names:
            raise ValueError(_('Option %(option_name)s already defined in '
                               '%(registry)s') %
                             {'option_name': option.option_name,
                              'registry': self._registry_type})
        self._registered_options[option.option_id] = option


class ResourceOption(object):

    def __init__(self, option_id, option_name, validator=_validator):
        """The base object to define the option(s) to be stored in the DB.

        :param option_id: The ID of the option. This will be used to lookup
                          the option value from the DB and should not be
                          changed once defined as the values will no longer
                          be correctly mapped to the keys in the user_ref when
                          retrieving the data from the DB.
        :type option_id: str
        :param option_name: The name of the option. This value will be used
                            to map the value from the user request on a
                            resource update to the correct option id to be
                            stored in the database. This value should not be
                            changed once defined as it will change the
                            resulting keys in the user_ref.
        :type option_name: str
        :param validator: A callable that raises TypeError if the value to be
                          persisted is incorrect. A single argument of the
                          value to be persisted will be passed to it. No return
                          value is expected.
        :type validator: callable
        """
        if not isinstance(option_id, six.string_types) and len(option_id) == 4:
            raise TypeError(_('`option_id` must be a string, got %r')
                            % option_id)
        elif len(option_id) != 4:
            raise ValueError(_('`option_id` must be 4 characters in '

                               'length. Got %r') % option_id)
        if not isinstance(option_name, six.string_types):
            raise TypeError(_('`option_name` must be a string. '
                              'Got %r') % option_name)

        self._option_id = option_id
        self._option_name = option_name
        self.validator = validator

    @property
    def option_name(self):
        # NOTE(notmorgan) Option IDs should never be set outside of definition
        # time.
        return self._option_name

    @property
    def option_id(self):
        # NOTE(notmorgan) Option IDs should never be set outside of definition
        # time.
        return self._option_id
