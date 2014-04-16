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

from keystone.common import utils


class Hints(list):
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

    @classmethod
    def build(cls, context, supported_filters):
        """Build list hints based on the context query string.

        :param context: contains the query_string from which any list hints can
                        be extracted
        :param supported_filters: list of filters supported, so ignore any
                                  keys in query_dict that are not in this list.

        """
        query_dict = context['query_string']
        hints = cls()

        if query_dict is None:
            return hints

        for key in query_dict:
            # Check if this is an exact filter
            if supported_filters is None or key in supported_filters:
                hints.add_filter(key, query_dict[key])
                continue

            # Check if it is an inexact filter
            for valid_key in supported_filters:
                # See if this entry in query_dict matches a known key with an
                # inexact suffix added.  If it doesn't match, then that just
                # means that there is no inexact filter for that key in this
                # query.
                if not key.startswith(valid_key + '__'):
                    continue

                base_key, comparator = key.split('__', 1)

                # We map the query-style inexact of, for example:
                #
                # {'email__contains', 'myISP'}
                #
                # into a list directive add filter call parameters of:
                #
                # name = 'email'
                # value = 'myISP'
                # comparator = 'contains'
                # case_sensitive = True

                case_sensitive = True
                if comparator.startswith('i'):
                    case_sensitive = False
                    comparator = comparator[1:]
                hints.add_filter(base_key, query_dict[key],
                                 comparator=comparator,
                                 case_sensitive=case_sensitive)

        # NOTE(henry-nash): If we were to support pagination, we would pull any
        # pagination directives out of the query_dict here, and add them into
        # the hints list.
        return hints

    def add_filter(self, name, value, comparator='equals',
                   case_sensitive=False):
        self.append({'name': name, 'value': value, 'comparator': comparator,
                     'case_sensitive': case_sensitive, 'type': 'filter'})

    def filters(self):
        """Iterate over all unsatisfied filters.

        Each filter term consists of:

        * ``name``: the name of the attribute being matched
        * ``value``: the value against which it is being matched
        * ``comparator``: the operation, which can be one of ``equals``,
                          ``startswith`` or ``endswith``
        * ``case_sensitive``: whether any comparison should take account of
                              case
        * ``type``: will always be 'filter'

        """
        return [x for x in self if x['type'] == 'filter']

    def get_exact_filter_by_name(self, name):
        """Return a filter key and value if exact filter exists for name."""
        for entry in self:
            if (entry['type'] == 'filter' and entry['name'] == name and
                    entry['comparator'] == 'equals'):
                return entry

    def set_limit(self, limit, truncated=False):
        """Set a limit to indicate the list should be truncated."""
        # We only allow one limit entry in the list, so if it already exists
        # we overwrite the old one
        for x in self:
            if x['type'] == 'limit':
                x['limit'] = limit
                x['truncated'] = truncated
                break
        else:
            self.append({'limit': limit, 'type': 'limit',
                         'truncated': truncated})

    def get_limit(self):
        """Get the limit to which the list should be truncated."""
        for x in self:
            if x['type'] == 'limit':
                return x

    def apply_attribute_filters(self, refs):
        """Filters a list of references by filter values."""

        def _attr_match(ref_attr, val_attr):
            """Matches attributes allowing for booleans as strings.

            We test explicitly for a value that defines it as 'False',
            which also means that the existence of the attribute with
            no value implies 'True'

            """
            if type(ref_attr) is bool:
                return ref_attr == utils.attr_as_boolean(val_attr)
            else:
                return ref_attr == val_attr

        def _inexact_attr_match(filter, ref):
            """Applies an inexact filter to a result dict.

            :param filter: the filter in question
            :param ref: the dict to check

            :returns True if there is a match

            """
            comparator = filter['comparator']
            key = filter['name']

            if key in ref:
                filter_value = filter['value']
                target_value = ref[key]
                if not filter['case_sensitive']:
                    # We only support inexact filters on strings so
                    # it's OK to use lower()
                    filter_value = filter_value.lower()
                    target_value = target_value.lower()

                if comparator == 'contains':
                    return (filter_value in target_value)
                elif comparator == 'startswith':
                    return target_value.startswith(filter_value)
                elif comparator == 'endswith':
                    return target_value.endswith(filter_value)
                else:
                    # We silently ignore unsupported filters
                    return True

            return False

        for filter in self.filters():
            if filter['comparator'] == 'equals':
                attr = filter['name']
                value = filter['value']
                refs = [r for r in refs if _attr_match(
                    utils.flatten_dict(r).get(attr), value)]
            else:
                # It might be an inexact filter
                refs = [r for r in refs if _inexact_attr_match(
                    filter, r)]

        return refs

    def apply_limits(self, refs):
        """Limits a list of entities.

        The underlying driver layer may have already truncated the collection
        for us, but in case it was unable to handle truncation we check here.

        :param refs: the list of members of the collection
        :param hints: hints, containing, among other things, the limit
                      requested

        :returns: boolean indicating whether the list was truncated, as well
                  as the list of (truncated if necessary) entities.

        """
        NOT_LIMITED = False
        LIMITED = True

        list_limit = self.get_limit()
        if list_limit is None:
            # No truncation was requested
            return NOT_LIMITED, refs

        if list_limit.get('truncated', False):
            # The driver did truncate the list
            return LIMITED, refs

        if len(refs) > list_limit['limit']:
            # The driver layer wasn't able to truncate it for us, so we must
            # do it here
            return LIMITED, refs[:list_limit['limit']]

        return NOT_LIMITED, refs
