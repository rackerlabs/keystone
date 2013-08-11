# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

import uuid

from keystone import exception


# TODO(henry-nash) Include the supported inexact filters in this array to
# trigger support in the code, once the appropriate api reviews are complete
# for IceHouse.  Inexact filters currently planned for support are:
# 'contains', 'icontains', 'startswith', 'istartswith', 'endswith', 'iendswith'
INEXACT_FILTERS_SUPPORTED = []
INEXACT_QUERY_FILTERS_SUPPORTED = []


class ListDirectives(object):
    """Encapsulate directives for listing entities.

    List directives are modifiers that affect the return of entities from a
    list_<entities> operation.  They are typically passed to a driver to give
    direction as to what filtering and pagination actions are being requested.

    It is optional for a driver to action some or all of the list directives,
    but any filters that it does satisfy must be marked as such by calling
    mark_filter_satisfied().

    A ListDirective object can be instantiated empty and have filter and
    pagination directives added one at a time, or alternatively a
    controller style context query_string and a set of valid filters may be
    passed at instantiation time, which will cause it to build the appropriate
    list directives ready to be passed to a driver.

    """

    def __init__(self, query_dict=None, valid_filters=None):
        """Initialize the directives, optionally filling with query.

        :param query_dict: a controller style dict of queries of the form
                           {name : value, name : value....}
        :param valid_filters: list of filters supported, so ignore any filter
                              keys in query_dict that are not in this list. If
                              valid_filters is None and query_dict is defined
                              then assume all contents of query_dict are valid
                              and are filters.

        """
        self._filters = {}
        self._paginators = {}
        self._extras = {}
        self._endoflist = False

        if query_dict is None:
            return

        # Process the query_dict so that:
        #
        # 1) Any attributes that are also in valid_filters are added to the
        #    _filters dict
        # 2) if the page or per_page attributes are present, then load the
        #    values into the _paginators dict
        # 3) Any remaining attributes are inserted into the _extra dict,
        #    to allow for extensions that want to hook into other types
        #    of query data.  The _extra attributes will not be processed
        #    by the core drivers
        qdict = query_dict.copy()
        for key in query_dict:
            # Check if this is an exact filter
            if valid_filters is None or key in valid_filters:
                self.add_filter(key, query_dict[key])
                qdict.pop(key)
                continue

            # Check if it is an inexact filter
            for valid_key in valid_filters:
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
                    # casesensitive = True

                    casesensitive = True
                    comparator = inexact
                    if inexact.startswith('i'):
                        casesensitive = False
                        comparator = inexact[1:]
                    self.add_filter(base_key, query_dict[key],
                                    comparator=comparator,
                                    casesensitive=casesensitive)
                    qdict.pop(key)

        # If pagination elements exist, process them
        if 'page' in qdict:
            self.add_pageinator('page', qdict.pop('page'))
        if 'per_page' in qdict:
            self.add_pageinator('page_size', qdict.pop('per_page'))

        # Anything left over gets put in extra
        for key in qdict:
            self.add_extra(key, qdict[key])

    def add_filter(self, name, value, comparator='equals',
                   casesensitive=False):
        new_filter = {'name': name, 'value': value, 'comparator': comparator,
                      'casesensitive': casesensitive}
        self._filters[uuid.uuid4().hex] = new_filter

    def add_pageinator(self, name, value):
        new_paginator = {'name': name, 'value': value}
        self._paginators[uuid.uuid4().hex] = new_paginator

    def add_extra(self, name, value):
        new_extra = {'name': name, 'value': value}
        self._extras[uuid.uuid4().hex] = new_extra

    def filter_items(self):
        """Iterate over all unsatisfied filters.

        Will iterate over the filters returning key value pairs where

        key - the filter id (which can be passed to mark_filter_satisfied())
        value - dict of filter terms

        Filter terms consist of:

        name: the name of the attribute being matched
        value: the value against which it is being matched
        comapartor: the operation, currently only 'equals' is supported,
                    although see INEXACT_FILTERS_SUPPORTED at start of
                    file for future plans.
        casesensitive: whether any comparison should take account of case

        """
        return self._filters.items()

    def paginator_items(self):
        return self._paginators.items()

    def extra_items(self):
        return self._extras.items()

    def get_exact_filter_by_name(self, name):
        """Return a filter key and value if exact filter exists for name."""
        for fkey, filter in self.filter_items():
            if filter['name'] == name and filter['comparator'] == 'equals':
                return (fkey, filter)
        return (None, None)

    def mark_filter_satisfied(self, id):
        self._filters.pop(id, None)

    def mark_end_of_list(self):
        self._endoflist = True

    def is_end_of_list(self):
        return self._endoflist
