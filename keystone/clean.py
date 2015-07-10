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
import socket

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


def check_endpoint_url(url):
    """Validate url like '"http://127.0.0.1:8774 /v1.1/\$(tenant_i d)s"'

    When the url is not valid, should suppress it

    The invalid urls are as follows:
    1. a url which is None
    2. a url which has space, you can't use www.go o gle.com to search
    3. a url whose scheme is not 'http' or 'https'
    4. a url whose host in not valid
    5. a url whose port is greater than 65535(if the url has port)
    """
    # valid url should not be None
    if not url:
        return False

    # url with space is invalid
    if ' ' in url:
        return False

    # parse url and analyze the result
    res = parse.urlparse(url)
    scheme = res.scheme
    netloc = res.netloc
    path = res.path

    # scheme should be http or https
    if scheme != 'http' and scheme != 'https':
        return False

    # check whether netloc is invalid or not
    port = None
    if netloc and netloc.find(':') != -1:
        netloc, port = netloc.split(':')
    try:
        socket.gethostbyname(netloc)
    except Exception:
        LOG.warning('%s is not a valid host or ip.', netloc)
        return False

    if port and int(port) > 65535:
        return False

    # check whether the property in the path is exactly the same
    # with that in the WHITELISTED_PROPERTIES below
    WHITELISTED_PROPERTIES = {
        'tenant_id': 'tenant_id', 'user_id': 'user_id',
        'public_bind_host': 'public_bind_host',
        'admin_bind_host': 'admin_bind_host',
        'compute_host': 'compute_host',
        'admin_port': 'admin_port',
        'public_port': 'public_port',
        'public_endpoint': 'public_endpoint',
        'admin_endpoint': 'admin_endpoint'}

    if path:
        path = path.replace('$', '%')
        try:
            path = path % WHITELISTED_PROPERTIES
        except Exception:
            LOG.warning('The path has error.')
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
