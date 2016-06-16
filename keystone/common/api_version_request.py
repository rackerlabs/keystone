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

import re

from keystone import exception
from keystone.i18n import _

# Define the minimum and maximum version of the API across all of the
# REST API. The format of the version is:
# X.Y where:
#
# - X will only be changed if a significant backwards incompatible API
# change is made which affects the API as whole. That is, something
# that is only very very rarely incremented.
#
# - Y when you make any change to the API. Note that this includes
# semantic changes which may not affect the input or output formats or
# even originate in the API code layer. We are not distinguishing
# between backwards compatible and backwards incompatible changes in
# the versioning system. It must be made clear in the documentation as
# to what is a backwards compatible change and what is a backwards
# incompatible one.
#
# The minimum and maximum versions of the API supported
# The default api version request is defined to be the
# the minimum version of the API supported.
_MIN_API_VERSION = "3.6"
_MAX_API_VERSION = "3.7"
DEFAULT_API_VERSION = _MIN_API_VERSION


# NOTE(henry-nash): min and max versions declared as functions so we can
# mock them for unittests. Do not use the constants directly anywhere
# but here.
def min_api_version():
    return APIVersionRequest(_MIN_API_VERSION)


def max_api_version():
    return APIVersionRequest(_MAX_API_VERSION)


def is_supported(req, min_version=_MIN_API_VERSION,
                 max_version=_MAX_API_VERSION):
    """Check if API request version satisfies version restrictions.

    :param req: request object
    :param min_version: minimal version of API needed for correct
           request processing
    :param max_version: maximum version of API needed for correct
           request processing

    :returns True if request satisfies minimal and maximum API version
             requirements. False in other case.
    """
    return (APIVersionRequest(max_version) >= req.api_version_request >=
            APIVersionRequest(min_version))


class APIVersionRequest(object):
    """API Version Request supporting manipulation of microversion numbers."""

    def __init__(self, version_string=None):
        """Create an API version request object.

        :param version_string: String representation of APIVersionRequest.
            Correct format is 'X.Y', where 'X' and 'Y' are int values.
            None value should be used to create Null APIVersionRequest,
            which is equal to 0.0
        """
        self.ver_major = 0
        self.ver_minor = 0

        if version_string is not None:
            match = re.match(r"^([1-9]\d*)\.([1-9]\d*|0)$",
                             version_string)
            if match:
                self.ver_major = int(match.group(1))
                self.ver_minor = int(match.group(2))
            else:
                raise exception.InvalidAPIVersionString(version=version_string)

    def __str__(self):
        """Debug/Logging representation of object."""
        return ("API Version Request Major: %s, Minor: %s"
                % (self.ver_major, self.ver_minor))

    def is_null(self):
        return self.ver_major == 0 and self.ver_minor == 0

    def _format_type_error(self, other):
        return TypeError(_("'%(other)s' should be an instance of '%(cls)s'") %
                         {"other": other, "cls": self.__class__})

    def __lt__(self, other):
        """True if request version is less than the one passed."""
        if not isinstance(other, APIVersionRequest):
            raise self._format_type_error(other)

        return ((self.ver_major, self.ver_minor) <
                (other.ver_major, other.ver_minor))

    def __eq__(self, other):
        """True if request version is equal to the one passed."""
        if not isinstance(other, APIVersionRequest):
            raise self._format_type_error(other)

        return ((self.ver_major, self.ver_minor) ==
                (other.ver_major, other.ver_minor))

    def __gt__(self, other):
        """True if request version is greater than the one passed."""
        if not isinstance(other, APIVersionRequest):
            raise self._format_type_error(other)

        return ((self.ver_major, self.ver_minor) >
                (other.ver_major, other.ver_minor))

    def __le__(self, other):
        """True if request version is less or equal to the one passed."""
        return self < other or self == other

    def __ne__(self, other):
        """True if request version is not equal to the one passed."""
        return not self.__eq__(other)

    def __ge__(self, other):
        """True if request version is greater or equal to the one passed."""
        return self > other or self == other

    def matches(self, min_version, max_version):
        """Determine if version object matches version range.

        Returns whether the version object represents a version
        greater than or equal to the minimum version and less than
        or equal to the maximum version.

        :param min_version: Minimum acceptable version.
        :param max_version: Maximum acceptable version.
        :returns boolean
        :raises ValueError

        If min_version is null then there is no minimum limit.
        If max_version is null then there is no maximum limit.
        If self is null then raise ValueError.
        """
        if self.is_null():
            raise ValueError
        if max_version.is_null() and min_version.is_null():
            return True
        elif max_version.is_null():
            return min_version <= self
        elif min_version.is_null():
            return self <= max_version
        else:
            return min_version <= self <= max_version

    def get_string(self):
        """Generate string representation of versioned request."""
        if self.is_null():
            raise ValueError
        return "%s.%s" % (self.ver_major, self.ver_minor)
