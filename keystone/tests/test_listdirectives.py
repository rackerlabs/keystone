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


from keystone.tests import core as test

from keystone.common import listdirectives


class ListDirectiveTests(test.TestCase):

    def test_create_iterate_satisfy(self):
        directives = listdirectives.ListDirectives(
            query_dict={'t1': 'data1', 't2': 'data2', 'myattr': 'data'},
            supported_filters=['t1', 't2', 't3'])
        filter_count = 0
        for fk, filters in directives.filter_items():
            filter_count += 1
        self.assertEqual(filter_count, 2)
        fk1, filter = directives.get_exact_filter_by_name('t1')
        self.assertEqual(filter['name'], 't1')
        self.assertEqual(filter['value'], 'data1')
        self.assertEqual(filter['comparator'], 'equals')
        self.assertEqual(filter['case_sensitive'], False)

        directives.mark_filter_satisfied(fk1)
        filter_count = 0
        for fk, filter in directives.filter_items():
            filter_count += 1
            self.assertEqual(filter['name'], 't2')
        self.assertEqual(filter_count, 1)

        extra_count = 0
        for ek, extra in directives.extra_items():
            extra_count += 1
            self.assertEqual(extra['name'], 'myattr')
            self.assertEqual(extra['value'], 'data')
        self.assertEqual(extra_count, 1)

    def test_multiple_creates(self):
        directives = listdirectives.ListDirectives(
            query_dict={'t1': 'data1', 't2': 'data2', 't3': 'data3'},
            supported_filters=['t1', 't2'])
        filter_count = 0
        for fk, filters in directives.filter_items():
            filter_count += 1
        self.assertEqual(filter_count, 2)
        directives2 = listdirectives.ListDirectives(
            query_dict={'t4': 'data1', 't5': 'data2'})
        filter_count = 0
        for fk, filters in directives2.filter_items():
            filter_count += 1
        self.assertEqual(filter_count, 2)
