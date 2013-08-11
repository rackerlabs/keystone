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


class ListDirectives(object):
    """Encapsulate directives for listing entities.

    List directives are modifiers that affect the return of entities from a
    list_<entities> operation.  They are typically passed to a driver to give
    direction as to what filtering and pagination actions are being requested.

    It is optional for a driver to action some or all of the list directives,
    but any filters that is does satisfy must be marked as such by calling
    markfiltersatisfied().

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
                              then assume all contents of query_dict are valid.

        """
        self.filters = {}
        self.paginators = {}
        self.endoflist = False

        for key in query_dict:
            if valid_filters is None or key in valid_filters:
                self.addfilter(key, query_dict[key])
                continue

            # Check if it is an inexact filter
            if valid_filters:
                for valid_key in valid_filters:
                    if key.startswith(valid_key + '__'):
                        base_key, inexact = key.split('__', 1)
                        if inexact not in INEXACT_FILTERS_SUPPORTED:
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
                        self.addfilter(base_key, query_dict[key],
                                       comparator=comparator,
                                       casesensitive=casesensitive)

            # TODO(henry-nash) Check for any pagination directives in the
            # query sting and add those in too

    def addfilter(self, name, value, comparator='equals', casesensitive=False):
        new_filter = {'name': name, 'value': value, 'comparator': comparator,
                      'casesensitive': casesensitive}
        self.filters[uuid.uuid4().hex] = new_filter

    def addpageindex(self, value):
        self.paginators['page'] = value

    def addpagesize(self, value):
        self.paginators['pagesize'] = value

    def filteritems(self):
        """Iterate over all unsatisfied filters."""
        return self.filters.items()

    def paginatoritems(self):
        return self.paginators.items()

    def getexactfilterbyname(self, name):
        """Return a filter key and value if exact filter exists for name."""
        for fkey, filter in self.filteritems():
            if filter['name'] == name and filter['comparator'] == 'equals':
                return (fkey, filter)
        return (None, None)

    def markfiltersatisfied(self, id):
        self.filters.pop(id, None)

    def markendoflist(self):
        self.endoflist = True

    def isendoflist(self):
        return self.endoflist
