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

import ldap.dn as ldap_dn
import ldap.filter as ldap_filter
import six


class Attr(object):
    def __init__(self, name):
        self.name = name

    def __and__(self, other):
        raise NotImplementedError("'&' is not supported for attrs. "
                                  "Forgot braces?")

    def __eq__(self, value):
        if isinstance(value, Attr):
            raise NotImplementedError("'==' is not supported when Attr's "
                                      "object is right operand.")
        return Equality(self.name, value)

    def __str__(self):
        return self.name


class FilterExpr(object):
    def __and__(self, other):
        return Conjunction(self, other)

    def __or__(self, other):
        return Disjunction(self, other)

    def __eq__(self, value):
        raise NotImplementedError("'==' is not supported for exprs. "
                                  "Forgot braces?")


class Equality(FilterExpr):
    def __init__(self, attr, value):
        self.attr = attr
        self.value = value

    def __str__(self):
        value = ldap_filter.escape_filter_chars(self.value)
        return u'(%s=%s)' % (self.attr, value)


class Junction(Equality):
    def __init__(self, *parts):
        super(Junction, self).__init__(*parts)
        self.parts = []
        for part in parts:
            if isinstance(part, Junction):
                self.parts += part.parts
            else:
                self.parts.append(part)


class Conjunction(Junction):
    def __str__(self):
        return u'(&%s)' % (u''.join(map(six.text_type, self.parts)),)


class Disjunction(Junction):
    def __str__(self):
        return u'(|%s)' % (u''.join(map(six.text_type, self.parts)),)


class DN(object):
    def __init__(self, *parts):
        self.parts = parts

    def __str__(self):
        parts = []
        for part in self.parts:
            if isinstance(part, tuple):
                attr, val = part
                val = ldap_dn.escape_dn_chars(six.text_type(val))
                parts.append(u'%s=%s,' % (attr, val))
            else:
                parts.append(six.text_type(part))
        return u'%s' % (u''.join(parts),)

    def __radd__(self, other):
        if not isinstance(other, tuple):
            raise NotImplementedError("Only tuples are supported "
                                      "in expressions like this.")
        if len(other) != 2:
                raise NotImplementedError("Only two-element tuples are "
                                          "supported in expressions like "
                                          "this. Forgot braces?")
        return DN(other, *self.parts)

    def __add__(self, other):
        raise NotImplementedError("'DN + attrs' is not supported "
                                  "for DN. Please, use 'attrs + DN'.")


objectClass = Attr('objectClass')
ALL = 'objectClass=*'
EMPTY_ADDEND = ''
