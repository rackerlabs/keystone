# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import functools

from keystone.openstack.common import importutils


def response_truncated(f):
    """Truncate the list returned by the wrapped function.

    This is designed to wrap Manager list_{entity} methods to ensure that
    any list limits are enforced.  Provided a Hints list is provided, the
    wrapper will insert the correct limit into the Hints so that the underlying
    driver call can try and honor it.  In fact, because we want the caller
    to be able to determine if the list has been truncated, it actually asks
    the driver for one more entity than the limit, but will set the limit
    in the hint to the correct value before returning to the caller.

    A _get_list_limit() method is required to be present in the object
    class hierarchy, which returns the limit to which we will truncate.

    If a Hints list is not provided an internal call is being made to a method protected by this
    wrapper and list limiting is NOT required, then calling it without a
    Hints list will cause any limit set to be ignored.

    """
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        if 'hints' not in kwargs:
            return f(self, *args, **kwargs)
        else:
            list_limit = self.driver._get_list_limit()
            if list_limit:
                # Ask for one more entry than we need
                kwargs['hints'].set_limit(list_limit + 1)
            ref_list = f(self, *args, **kwargs)
            if list_limit:
                # Set the limit to the correct value, so the caller can
                # determine if we have too many entries
                kwargs['hints'].set_limit(list_limit)
            return ref_list
    return wrapper


class Manager(object):
    """Base class for intermediary request layer.

    The Manager layer exists to support additional logic that applies to all
    or some of the methods exposed by a service that are not specific to the
    HTTP interface.

    It also provides a stable entry point to dynamic backends.

    An example of a probable use case is logging all the calls.

    """

    def __init__(self, driver_name):
        self.driver = importutils.import_object(driver_name)

    def __getattr__(self, name):
        """Forward calls to the underlying driver."""
        f = getattr(self.driver, name)

        @functools.wraps(f)
        def _wrapper(*args, **kw):
            return f(*args, **kw)
        setattr(self, name, _wrapper)
        return _wrapper
