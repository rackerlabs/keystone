# Copyright 2015 OpenStack Foundation
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

import six
import testtools

from keystone.common.ldap import expr
from keystone import tests


class ExprTestBase(tests.TestCase):
    @staticmethod
    def _get_bad_name():
        name = uuid.uuid4().hex
        parts = name[:len(name) / 2], name[len(name) / 2:]
        return '\\'.join(parts), '\\\\'.join(parts), '\\5c'.join(parts)

    def setUp(self):
        super(ExprTestBase, self).setUp()
        self.attrs = []
        self.values = []
        self.values_dn = []
        self.values_filter = []
        for i in xrange(3):
            self.attrs.append(self._get_bad_name()[0])
            val, val_dn, val_filter = self._get_bad_name()
            self.values.append(val)
            self.values_dn.append(val_dn)
            self.values_filter.append(val_filter)


class DNExprTest(ExprTestBase):
    def setUp(self):
        super(DNExprTest, self).setUp()
        self.tree_dn = '%s=%s' % (self.attrs[2], self.values_dn[2])

    def test_radd_instance(self):
        """Test instance of result of right adding."""
        dn_expr = (self.attrs[0], self.values[0]) + expr.DN(self.tree_dn)
        self.assertIsInstance(dn_expr, expr.DN)

    def test_radd_to_added_instance(self):
        """Test instance of result of another right adding."""
        dn_expr = ((self.attrs[0], self.values[0]) +
                   ((self.attrs[1], self.values[1]) +
                    expr.DN(self.tree_dn)))
        self.assertIsInstance(dn_expr, expr.DN)

    def build_expression(self):
        dn_str = u'%s=%s,%s' % (self.attrs[0], self.values_dn[0], self.tree_dn)
        dn_expr = (self.attrs[0], self.values[0]) + expr.DN(self.tree_dn)
        return dn_str, dn_expr

    def test_right_building(self):
        """Test right expression building."""
        dn_str, dn_expr = self.build_expression()
        self.assertEqual(dn_str, six.text_type(dn_expr))

    def test_radd_new_attr(self):
        """Test adding another attribute to dn."""
        dn_str, dn_expr = self.build_expression()
        dn_expr = (self.attrs[1], self.values[1]) + dn_expr
        dn_str = u'%s=%s,%s' % (self.attrs[1], self.values_dn[1], dn_str)
        self.assertEqual(dn_str, six.text_type(dn_expr))

    def test_skipped_braces(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type(
                (self.attrs[0], self.values[0]) +
                (self.attrs[1], self.values[1]) +
                expr.DN(self.tree_dn)
            )

    def test_wrong_add_operation(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type(
                expr.DN(self.tree_dn) +
                (self.attrs[0], self.values[0])
            )

    def test_wrong_attribute_presentation(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type(
                (self.attrs[0], self.attrs[1], self.values[0]) +
                expr.DN(self.tree_dn)
            )

    def test_wrong_expr_building(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type(expr.DN(self.attrs[0]) + expr.DN(self.values[0]))


class FilterExprTest(ExprTestBase):
    def test_global_fields(self):
        self.assertEqual(six.text_type(expr.FilterExpr.ALL), '(objectClass=*)')

    def test_eq_result_instance(self):
        """Test instance of result of equality operation."""
        filter_expr = expr.Attr(self.attrs[0]) == self.values[0]
        self.assertIsInstance(filter_expr, expr.Equality)

    def test_eq_star_guard(self):
        with testtools.ExpectedException(NotImplementedError):
            expr.Attr(self.attrs[0]) == '*'

    def test_eq_star(self):
        self.assertEqual(
            '(%s=*)' % (self.attrs[0],),
            six.text_type(expr.Attr(self.attrs[0]) == expr.STAR),
        )

    def test_eq_star_within(self):
        self.assertEqual(
            '(%s=%s\\2a)' % (self.attrs[0], self.values_filter[0]),
            six.text_type(expr.Attr(self.attrs[0]) == (self.values[0] + '*')),
        )

    def test_and_result_instance(self):
        """Test instance of result of conjunction."""
        filter_expr = ((expr.Attr(self.attrs[0]) == self.values[0]) &
                       (expr.Attr(self.attrs[1]) == self.values[1]))
        self.assertIsInstance(filter_expr, expr.Conjunction)

    def test_right_eq_building(self):
        self.assertEqual(
            u'(%s=%s)' % (self.attrs[0], self.values_filter[0]),
            six.text_type(expr.Attr(self.attrs[0]) == self.values[0]),
        )

    def test_right_and_expr_building(self):
        filter_str = u'(&(%s=%s)(%s=%s))' % (
            self.attrs[0], self.values_filter[0],
            self.attrs[1], self.values_filter[1],
        )
        filter_expr = ((expr.Attr(self.attrs[0]) == self.values[0]) &
                       (expr.Attr(self.attrs[1]) == self.values[1]))
        self.assertEqual(filter_str, six.text_type(filter_expr))

    def test_queryparams_building(self):
        filter_str = u'(&(%s=%s)(%s=%s))' % (
            self.attrs[0], self.values_filter[0],
            self.attrs[1], self.values_filter[1],
        )
        filter_expr = ((expr.Attr(self.attrs[0]) == self.values[0]) &
                       {self.attrs[1]: self.values[1]})
        self.assertEqual(filter_str, six.text_type(filter_expr))

    def test_skipped_braces_right_addend(self):
        """Test skipped braces, which must surround right operand of '&'."""
        with testtools.ExpectedException(NotImplementedError):
            ((expr.Attr(self.attrs[0]) == self.values[0]) &
             expr.Attr(self.attrs[1]) == self.values[1])

    def test_skipped_braces_left_addend(self):
        """Test skipped braces, which must surround left operand of '&'."""
        with testtools.ExpectedException(TypeError):
            (expr.Attr(self.attrs[0]) == self.values[0] &
             (expr.Attr(self.attrs[1]) == self.values[1]))

    def test_skipped_braces_both_addend(self):
        """Test skipped braces, which must surround both operands of '&'."""
        with testtools.ExpectedException(TypeError):
            (expr.Attr(self.attrs[0]) == self.values[0] &
             expr.Attr(self.attrs[1]) == self.values[1])

    def test_wrong_add(self):
        with testtools.ExpectedException(NotImplementedError):
            (expr.Attr(self.attrs[0]) & self.values[0])

    def test_wrong_add_two_attrs(self):
        with testtools.ExpectedException(NotImplementedError):
            (expr.Attr(self.attrs[0]) & expr.Attr(self.attrs[1]))

    def test_wrong_eq_operation(self):
        with testtools.ExpectedException(NotImplementedError):
            (expr.Attr(self.attrs[0]) == expr.Attr(self.values[0]))

    def test_or_result_instance(self):
        """Test instance of result of conjunction."""
        filter_expr = ((expr.Attr(self.attrs[0]) == self.values[0]) |
                       (expr.Attr(self.attrs[1]) == self.values[1]))
        self.assertIsInstance(filter_expr, expr.Disjunction)

    def test_right_or_expr_building(self):
        filter_str = u'(|(%s=%s)(%s=%s))' % (
            self.attrs[0], self.values_filter[0],
            self.attrs[1], self.values_filter[1],
        )
        filter_expr = ((expr.Attr(self.attrs[0]) == self.values[0]) |
                       (expr.Attr(self.attrs[1]) == self.values[1]))
        self.assertEqual(filter_str, six.text_type(filter_expr))

    def test_nested_junctions(self):
        filter_str = u'(|(%s=%s)(&(%s=%s)(%s=%s)))' % (
            self.attrs[0], self.values_filter[0],
            self.attrs[1], self.values_filter[1],
            self.attrs[2], self.values_filter[2],
        )
        filter_expr = ((expr.Attr(self.attrs[0]) == self.values[0]) |
                       (expr.Attr(self.attrs[1]) == self.values[1]) &
                       (expr.Attr(self.attrs[2]) == self.values[2]))
        self.assertEqual(filter_str, six.text_type(filter_expr))
