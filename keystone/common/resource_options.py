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

"""Options specific to resources managed by Keystone (Domain, User, etc)"""


import collections

import six

from keystone.i18n import _


class _FrozenDict(collections.Mapping):
    # NOTE(notmorgan) Used to prevent code from mucking with values in the
    # option registry.

    def __init__(self, data):
        self._data = data

    def __getitem__(self, item):
        return self._data[item]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class ResourceOptionRegistry(object):
    def __init__(self, registry_name):
        self._registered_options = {}
        self._registry_type = registry_name

    @property
    def option_names(self):
        return set([opt.option_name
                    for opt in self._registered_options.values()])

    @property
    def options(self):
        return _FrozenDict(self._registered_options)

    def register_option(self, option):
        if option.option_id in self._registered_options:
            raise ValueError(_('Option %(option_id)d already defined in '
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
    def __str__(self):
        return 'Option<%(id)s %(opt_id)d, Name %(name)s>' % {
            'id': id(self), 'opt_id': self.option_id, 'name': self.option_name}

    def __repr__(self):
        return ('ResourceOption(option_id="%(opt_id)d", '
                'option_name="%(name)s")' %
                {'opt_id': self.option_id, 'name': self.option_name})

    def __init__(self, option_id, option_name, datatype):
        """The base object to define the option(s) to be stored in the DB.

        :param option_id: The ID of the option. This will be used to lookup
                          the option value from the DB and should not be
                          changed once defined as the values will no longer
                          be correctly mapped to the keys in the user_ref when
                          retrieving the data from the DB.
        :type option_id: int
        :param option_name: The name of the option. This value will be used
                            to map the value from the user request on a
                            resource update to the correct option id to be
                            stored in the database. This value should not be
                            changed once defined as it will change the
                            resulting keys in the user_ref.
        :type option_name: str
        :param datatype: Python Primitive that the datatype should be validated
                         against when storing the value to the database.
        :type datatype: python primitive type
        """
        if isinstance(option_id, int):
            self._option_id = option_id
        else:
            raise TypeError('option_id must be an integer.')

        if isinstance(option_name, six.string_types):
            self._option_name = option_name
        else:
            raise TypeError('option_name must be a string.')

        self._datatype = datatype

    def validate(self, value):
        """Validate the value when persisting to the backend.

        :raises: ValueError
        :returns: None
        """
        if not isinstance(value, self._datatype):
            raise ValueError(_('Option Value must be of type %(type)r, '
                               'received %(value)r.') %
                             {'type': self._datatype, 'value': value})

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


