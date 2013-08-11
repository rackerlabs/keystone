# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from keystone import exception


# TODO(henry-nash) Include the supported inexact filters in this array to
# trigger support in the code, once the appropriate api reviews are complete
# for IceHouse.  Inexact filters (as part of the query statement), currently
# planned for support are:
#
# 'contains', 'icontains', 'startswith', 'istartswith', 'endswith', 'iendswith'
#
# INEXACT_QUERY_FILTERS_SUPPORTED should be set to those that we support.
INEXACT_QUERY_FILTERS_SUPPORTED = []


class Hints(list):
    """Encapsulate driver hints for listing entities.

    Hints are modifiers that affect the return of entities from a
    list_<entities> operation.  They are typically passed to a driver to give
    direction as to what filtering and pagination actions are being requested.

    It is optional for a driver to action some or all of the list hints,
    but any filters that it does satisfy must be marked as such by calling
    mark_filter_satisfied().

    A Hint object can be instantiated empty and have filter hints added
    one at a time, or alternatively a controller style context
    query_string and a set of supported filters may be passed at instantiation
    time, which will cause the appropriate filter hints to be built.

    A Hint object is a list of dicts, initially all of type 'filter', although
    other types may be added in the future. The list can be enumerated
    directly, or by using the filter() method which will guarantee to only
    return filters.

    """

    def __init__(self, query_dict=None, supported_filters=None):
        """Initialize the hints, optionally filling with query.

        :param query_dict: a controller style dict of queries of the form
                           {name : value, name : value....}
        :param supported_filters: list of filters supported, so ignore any
                                  keys in query_dict that are not in this list.
                                  If supported_filters is None and query_dict
                                  is defined then assume all contents of
                                  query_dict are supported filters.

        """
        if query_dict is None:
            return

        for key in query_dict:
            # Check if this is an exact filter
            if supported_filters is None or key in supported_filters:
                self.add_filter(key, query_dict[key])
                continue

            # Check if it is an inexact filter
            for valid_key in supported_filters:
                # See if this entry in query_dict matches a known key with an
                # inexact suffix added.  If it doesn't match, then that just
                # means that there is no inexact filter for that key in this
                # query.
                if key.startswith(valid_key + '__'):
                    base_key, inexact = key.split('__', 1)
                    if inexact not in INEXACT_QUERY_FILTERS_SUPPORTED:
                        msg = (_('Unsupported inexact string filter: %s')
                               % inexact)
                        raise exception.ValidationError(msg)

                    # We map the query-style inexact of, for example:
                    #
                    # {'email_contains', 'myISP'}
                    #
                    # into a list directive add filter call parameters of:
                    #
                    # name = 'email'
                    # value = 'myISP'
                    # comparator = 'contains'
                    # case_sensitive = True

                    case_sensitive = True
                    comparator = inexact
                    if inexact.startswith('i'):
                        case_sensitive = False
                        comparator = inexact[1:]
                    self.add_filter(base_key, query_dict[key],
                                    comparator=comparator,
                                    case_sensitive=case_sensitive)

        # NOTE(henry-nash): If we were to support pagination, we would pull any
        # pagination directives out of the query_dict here, and add them into
        # a paginators dict.

    def add_filter(self, name, value, comparator='equals',
                   case_sensitive=False):
        self.append({'name': name, 'value': value, 'comparator': comparator,
                     'case_sensitive': case_sensitive, 'type': 'filter'})

    def filters(self):
        """Iterate over all unsatisfied filters.

        Each filter terms consist of:

        name: the name of the attribute being matched
        value: the value against which it is being matched
        comapartor: the operation, currently only 'equals' is supported,
                    although see INEXACT_FILTERS_SUPPORTED at start of
                    file for future plans.
        case_sensitive: whether any comparison should take account of case
        type: will always be 'filter'

        """
        return [x for x in self if x['type'] == 'filter']

    def get_exact_filter_by_name(self, name):
        """Return a filter key and value if exact filter exists for name."""
        for entry in self:
            if (entry['type'] == 'filter' and entry['name'] == name and
                    entry['comparator'] == 'equals'):
                return entry

    def mark_filter_satisfied(self, filter):
        self.remove(filter)
