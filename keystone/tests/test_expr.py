# Copyright 2012 OpenStack Foundation
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

import ldap
import six
import testtools

from keystone.common.ldap import expr
from keystone import tests


ID_ATTR = "cn"
OBJECT_CLASS = "groupOfNames"
OBJECT_ID = uuid.uuid4().hex
TREE_DN = "dc=example,dc=com"


class DNExprTest(tests.TestCase):
    def test_radd_instance(self):
        """Test instance of result of right adding."""
        filter_str = (ID_ATTR, OBJECT_ID) + expr.DN(TREE_DN)
        self.assertIsInstance(filter_str, expr.DN)

    def test_radd_to_added_instance(self):
        """Test instance of result of another right adding."""
        filter_str = ((expr.objectClass, OBJECT_CLASS) +
                      ((ID_ATTR, OBJECT_ID) + expr.DN(TREE_DN)))
        self.assertIsInstance(filter_str, expr.DN)

    def build_expression(self):
        filter_str = u'%s=%s,%s' % (ID_ATTR,
                                    ldap.dn.escape_dn_chars(
                                        six.text_type(OBJECT_ID)),
                                    TREE_DN)
        filter_str_expr = (ID_ATTR, OBJECT_ID) + expr.DN(TREE_DN)
        return filter_str, filter_str_expr

    def test_right_building(self):
        """Test right expression building."""
        filter_str, filter_str_expr = self.build_expression()
        self.assertEqual(filter_str, six.text_type(filter_str_expr))

    def test_radd_new_attr(self):
        """Test adding another attribute to dn."""
        filter_str, filter_str_expr = self.build_expression()
        filter_str_expr = ((expr.objectClass, OBJECT_CLASS) +
                           ((ID_ATTR, OBJECT_ID) + expr.DN(TREE_DN)))
        self.assertEqual(u'%s=%s,%s' % (expr.objectClass,
                                        OBJECT_CLASS,
                                        filter_str),
                         six.text_type(filter_str_expr))

    def test_skipped_braces(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type(
                ((ID_ATTR, OBJECT_ID) + (expr.objectClass, OBJECT_CLASS) +
                 expr.DN(TREE_DN)))

    def test_wrong_add_operation(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type((expr.DN(TREE_DN) + (ID_ATTR, OBJECT_ID)))

    def test_wrong_attribute_presentation(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type(((ID_ATTR, OBJECT_ID, OBJECT_CLASS) +
                           expr.DN(TREE_DN)))

    def test_wrong_expr_building(self):
        with testtools.ExpectedException(NotImplementedError):
            six.text_type((expr.DN(ID_ATTR) + expr.DN(TREE_DN)))


class AttrExprTest(tests.TestCase):
    def test_global_filed(self):
        self.assertEqual(six.text_type(expr.ALL), 'objectClass=*')
        self.assertEqual(six.text_type(expr.EMPTY_ADDEND), '')
        self.assertIsInstance(expr.objectClass, expr.Attr)

    def test_eq_result_instance(self):
        """Test instance of result of equality operation."""
        filter_str = expr.Attr(ID_ATTR) == OBJECT_ID
        self.assertIsInstance(filter_str, expr.Equality)

    def test_and_result_instance(self):
        """Test instance of result of conjunction."""
        filter_str = ((expr.Attr(ID_ATTR) == OBJECT_ID) &
                      (expr.objectClass == OBJECT_CLASS))
        self.assertIsInstance(filter_str, expr.Conjunction)

    def test_right_eq_building(self):
        self.assertEqual(
            six.text_type(expr.Attr(ID_ATTR) == OBJECT_ID),
            u'(%s=%s)' % (ID_ATTR, OBJECT_ID))

    def test_right_expr_building(self):
        filter_str = (u'(&(%(id_attr)s=%(id)s)(objectClass=%(objclass)s))' %
                      {'id_attr': ID_ATTR,
                       'id': OBJECT_ID,
                       'objclass': OBJECT_CLASS})
        filter_str_expr = ((expr.Attr(ID_ATTR) == OBJECT_ID) &
                           (expr.objectClass == OBJECT_CLASS))
        self.assertEqual(six.text_type(filter_str_expr), filter_str)

    def test_skipped_braces_right_addend(self):
        """Test skipped braces, which must surround right operand of '&'."""
        with testtools.ExpectedException(NotImplementedError):
            ((expr.Attr(ID_ATTR) == OBJECT_ID) &
             expr.objectClass == OBJECT_CLASS)

    def test_skipped_braces_left_addend(self):
        """Test skipped braces, which must surround left operand of '&'."""
        with testtools.ExpectedException(TypeError):
            (expr.Attr(ID_ATTR) == OBJECT_ID &
             (expr.objectClass == OBJECT_CLASS))

    def test_skipped_braces_both_addend(self):
        """Test skipped braces, which must surround both operands of '&'."""
        with testtools.ExpectedException(TypeError):
            (expr.Attr(ID_ATTR) == OBJECT_ID &
             expr.objectClass == OBJECT_CLASS)

    def test_wrong_add(self):
        with testtools.ExpectedException(NotImplementedError):
            (expr.Attr(ID_ATTR) & OBJECT_ID)

    def test_wrong_add_two_attrs(self):
        with testtools.ExpectedException(NotImplementedError):
            (expr.Attr(ID_ATTR) & expr.Attr(OBJECT_CLASS))

    def test_wrong_eq_operation(self):
        with testtools.ExpectedException(NotImplementedError):
            (expr.Attr(ID_ATTR) == expr.Attr(OBJECT_CLASS))

    def test_or_result_instance(self):
        """Test instance of result of conjunction."""
        filter_str = ((expr.Attr(ID_ATTR) == OBJECT_ID) |
                      (expr.objectClass == OBJECT_CLASS))
        self.assertIsInstance(filter_str, expr.Disjunction)

    def test_right_expr_with_or_building(self):
        filter_str = (u'(|(%(id_attr)s=%(id)s)(objectClass=%(objclass)s))' %
                      {'id_attr': ID_ATTR,
                       'id': OBJECT_ID,
                       'objclass': OBJECT_CLASS})
        filter_str_expr = ((expr.Attr(ID_ATTR) == OBJECT_ID) |
                           (expr.objectClass == OBJECT_CLASS))
        self.assertEqual(six.text_type(filter_str_expr), filter_str)