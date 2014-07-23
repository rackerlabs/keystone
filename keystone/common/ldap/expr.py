# Copyright 2014 Mirantis Inc
# All Rights Reserved.
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

from ldap import dn as ldap_dn
from ldap import filter as ldap_filter
import six


class Attr(object):
    def __init__(self, name):
        self.name = name

    def __and__(self, other):
        raise NotImplementedError("'&' is not supported for attrs. "
                                  "Forgot braces?")

    def __eq__(self, value):
        return Equality(self.name, value)

    def __str__(self):
        return self.name


class DN(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __radd__(self, other):
        return Addition(self.name, other)


class FilterExpr(object):
    def __and__(self, other):
        return Conjunction(self, other)

    def __eq__(self, value):
        raise NotImplementedError("'==' is not supported for exprs. "
                                  "Forgot braces?")

    def __radd__(self, other):
        return Addition(self, other)


class Addition(FilterExpr):
    def __init__(self, *parts):
        self.parts = []
        for part in parts:
            if isinstance(part, Addition):
                self.parts += part.parts
            elif isinstance(part, tuple):
                attr, value = part
                value = ldap_dn.escape_dn_chars(value)
                self.parts.append(u'%s=%s,' % (attr, value))
            else:
                self.parts.append(part)

    def __str__(self):
        return u'%s' % (u''.join(map(six.text_type, reversed(self.parts))),)


class Equality(FilterExpr):
    def __init__(self, attr, value):
        self.attr = attr
        self.value = value

    def __str__(self):
        value = ldap_filter.escape_filter_chars(self.value)
        return u'(%s=%s)' % (self.attr, value)


class Conjunction(FilterExpr):
    def __init__(self, *parts):
        self.parts = []
        for part in parts:
            if isinstance(part, Conjunction):
                self.parts += part.parts
            else:
                self.parts.append(part)

    def __str__(self):
        return u'(&%s)' % (u''.join(map(six.text_type, self.parts)),)

objectClass = Attr('objectClass')
ALL = objectClass == '*'
