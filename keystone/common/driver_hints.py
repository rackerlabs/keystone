# Copyright 2013 OpenStack Foundation
# Copyright 2013 IBM Corp.
#
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


class Hints(object):
    """Encapsulate driver hints for listing entities.

    Hints are modifiers that affect the return of entities from a
    list_<entities> operation.  They are typically passed to a driver to give
    direction as to what filtering, pagination or list limiting actions are
    being requested.

    It is optional for a driver to action some or all of the list hints,
    but any filters that it does satisfy must be marked as such by calling
    removing the filter from the list.

    A Hint object is a list of dicts, initially of type 'filter' or 'limit',
    although other types may be added in the future. The list can be enumerated
    directly, or by using the filters() method which will guarantee to only
    return filters.

    """
    def __init__(self):
        self._limit = None
        self._filters = list()

    def add_filter(self, name, value, comparator='equals',
                   case_sensitive=False):
        self._filters.append({'name': name, 'value': value,
                             'comparator': comparator,
                             'case_sensitive': case_sensitive,
                             'type': 'filter'})

    def filters(self):
        """Return all unsatisfied filters.

        Each filter term consists of:

        * ``name``: the name of the attribute being matched
        * ``value``: the value against which it is being matched
        * ``comparator``: the operation, which can be one of ``equals``,
                          ``startswith`` or ``endswith``
        * ``case_sensitive``: whether any comparison should take account of
                              case
        * ``type``: will always be 'filter'

        """
        return self._filters

    def get_exact_filter_by_name(self, name):
        """Return a filter key and value if exact filter exists for name."""
        for entry in self._filters:
            if (entry['type'] == 'filter' and entry['name'] == name and
                    entry['comparator'] == 'equals'):
                return entry

    def remove(self, _filter):
        """Removes a filter from the filters list.
        Will throw an exception if the filter is not in the list"""
        self._filters.remove(_filter)

    def set_limit(self, limit, truncated=False):
        """Set a limit to indicate the list should be truncated."""
        # We only allow one limit entry in the list, so if it already exists
        # we overwrite the old one
        self._limit = {'limit': limit, 'type': 'limit', 'truncated': truncated}

    def get_limit(self):
        """Get the limit to which the list should be truncated."""
        return self._limit
