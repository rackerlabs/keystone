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

from oslo_log import log
import six
from six.moves.urllib import parse

from keystone import exception
from keystone.i18n import _


LOG = log.getLogger(__name__)


def check_length(property_name, value, min_length=1, max_length=64):
    if len(value) < min_length:
        if min_length == 1:
            msg = _("%s cannot be empty.") % property_name
        else:
            msg = (_("%(property_name)s cannot be less than "
                   "%(min_length)s characters.") % dict(
                       property_name=property_name, min_length=min_length))
        raise exception.ValidationError(msg)
    if len(value) > max_length:
        msg = (_("%(property_name)s should not be greater than "
               "%(max_length)s characters.") % dict(
                   property_name=property_name, max_length=max_length))

        raise exception.ValidationError(msg)


def check_type(property_name, value, expected_type, display_expected_type):
    if not isinstance(value, expected_type):
        msg = (_("%(property_name)s is not a "
                 "%(display_expected_type)s") % dict(
                     property_name=property_name,
                     display_expected_type=display_expected_type))
        raise exception.ValidationError(msg)


def check_enabled(property_name, enabled):
    # Allow int and it's subclass bool
    check_type('%s enabled' % property_name, enabled, int, 'boolean')
    return bool(enabled)


def check_name(property_name, name, min_length=1, max_length=64):
    check_type('%s name' % property_name, name, six.string_types,
               'str or unicode')
    name = name.strip()
    check_length('%s name' % property_name, name,
                 min_length=min_length, max_length=max_length)
    return name


def check_endpoint_url(url, whitelist):
    """Validate url like '"http://127.0.0.1:8774 /v1.1/\$(tenant_i d)s"'

    When the url is not valid, should suppress it

    The invalid urls are as follows:
    1. a url which is None
    2. a url which has space, you can't use www.go o gle.com to search
    3. substitutions should be in the whitelist
    """
    # valid url should not be None
    if not url:
        return False

    # url with space is invalid
    if ' ' in url:
        return False

    # check whether the property in the path is exactly the same
    # with that in the WHITELISTED_PROPERTIES below
    WHITELISTED_PROPERTIES = {}
    for property in whitelist:
        WHITELISTED_PROPERTIES[property] = property

    path = parse.urlparse(url).path
    if path:
        path = path.replace('$', '%')
        try:
            path = path % WHITELISTED_PROPERTIES
        except Exception:
            LOG.warning('The path: %s has error.', path)
            return False

    return True


def domain_name(name):
    return check_name('Domain', name)


def domain_enabled(enabled):
    return check_enabled('Domain', enabled)


def project_name(name):
    return check_name('Project', name)


def project_enabled(enabled):
    return check_enabled('Project', enabled)


def user_name(name):
    return check_name('User', name, max_length=255)


def user_enabled(enabled):
    return check_enabled('User', enabled)


def group_name(name):
    return check_name('Group', name)
