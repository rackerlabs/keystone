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
import time
from types import FunctionType

from oslo_log import log
from oslo_log import versionutils
from oslo_utils import importutils
from oslo_utils import reflection
import six
import stevedore

from keystone.i18n import _


LOG = log.getLogger(__name__)


def response_truncated(f):
    """Truncate the list returned by the wrapped function.

    This is designed to wrap Manager list_{entity} methods to ensure that
    any list limits that are defined are passed to the driver layer.  If a
    hints list is provided, the wrapper will insert the relevant limit into
    the hints so that the underlying driver call can try and honor it. If the
    driver does truncate the response, it will update the 'truncated' attribute
    in the 'limit' entry in the hints list, which enables the caller of this
    function to know if truncation has taken place.  If, however, the driver
    layer is unable to perform truncation, the 'limit' entry is simply left in
    the hints list for the caller to handle.

    A _get_list_limit() method is required to be present in the object class
    hierarchy, which returns the limit for this backend to which we will
    truncate.

    If a hints list is not provided in the arguments of the wrapped call then
    any limits set in the config file are ignored.  This allows internal use
    of such wrapped methods where the entire data set is needed as input for
    the calculations of some other API (e.g. get role assignments for a given
    project).

    """
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        if kwargs.get('hints') is None:
            return f(self, *args, **kwargs)

        list_limit = self.driver._get_list_limit()
        if list_limit:
            kwargs['hints'].set_limit(list_limit)
        return f(self, *args, **kwargs)
    return wrapper


def load_driver(namespace, driver_name, *args):
    try:
        driver_manager = stevedore.DriverManager(namespace,
                                                 driver_name,
                                                 invoke_on_load=True,
                                                 invoke_args=args)
        return driver_manager.driver
    except RuntimeError as e:
        LOG.debug('Failed to load %r using stevedore: %s', driver_name, e)
        # Ignore failure and continue on.

    driver = importutils.import_object(driver_name, *args)

    msg = (_(
        'Direct import of driver %(name)r is deprecated as of Liberty in '
        'favor of its entrypoint from %(namespace)r and may be removed in '
        'N.') %
        {'name': driver_name, 'namespace': namespace})
    versionutils.report_deprecated_feature(LOG, msg)

    return driver


class _TraceMeta(type):
    """A metaclass that, in trace mode, will log entry and exit of methods.

    This metaclass automatically wraps all methods on the class when
    instantiated with a decorator that will log entry/exit from a method
    when keystone is run in Trace log level.
    """

    @staticmethod
    def wrapper(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            exc = None
            t = time.time()
            fn_info = None
            do_trace = LOG.logger.getEffectiveLevel() <= log.TRACE
            try:
                if do_trace:
                    fn_info = '.'.join([f.__class__.__name__, f.__name__])
                    LOG.trace('Call %s' % fn_info)
                ret_val = f(*args, **kwargs)
            except Exception as e:  # nosec
                exc = e
                raise
            finally:
                if do_trace:
                    subst = {
                        'rt': (time.time() - t),
                        'passed_args': ', '.join([
                            ', '.join(args),
                            ', '.join(['%(k)s=%(v)r' % {'k': k, 'v': v}
                                       for k, v in kwargs.items()]),
                        ]),
                        'function': fn_info,
                        'exception': exc,
                    }
                    if exc is not None:
                        msg = ('[%(rt)s] %(function)s'
                               '(%(passed_args)s) => raised '
                               '%(exception)r') % subst
                    else:
                        msg = ('[%(rt)s] %(function)s'
                               '(%(passed_args)s) => %(ret_val)r') % subst
                    LOG.trace(msg)
            return ret_val
        return wrapped

    def __new__(meta, classname, bases, class_dict):
        final_cls_dict = {}
        for attr_name, attr in class_dict.items():
            if type(attr) == FunctionType and not attr_name.startswith('_'):
                attr = _TraceMeta.wrapper(attr)
            final_cls_dict[attr_name] = attr
        return type.__new__(meta, classname, bases, final_cls_dict)


@six.add_metaclass(_TraceMeta)
class Manager(object):
    """Base class for intermediary request layer.

    The Manager layer exists to support additional logic that applies to all
    or some of the methods exposed by a service that are not specific to the
    HTTP interface.

    It also provides a stable entry point to dynamic backends.

    An example of a probable use case is logging all the calls.

    """

    driver_namespace = None

    def __init__(self, driver_name):
        self.driver = load_driver(self.driver_namespace, driver_name)

    def __getattr__(self, name):
        """Forward calls to the underlying driver."""
        f = getattr(self.driver, name)
        setattr(self, name, f)
        return f


def create_legacy_driver(driver_class):
    """Helper function to deprecate the original driver classes.

    The keystone.{subsystem}.Driver classes are deprecated in favor of the
    new versioned classes. This function creates a new class based on a
    versioned class and adds a deprecation message when it is used.

    This will allow existing custom drivers to work when the Driver class is
    renamed to include a version.

    Example usage:

        Driver = create_legacy_driver(CatalogDriverV8)

    """
    module_name = driver_class.__module__
    class_name = reflection.get_class_name(driver_class)

    class Driver(driver_class):

        @versionutils.deprecated(
            as_of=versionutils.deprecated.LIBERTY,
            what='%s.Driver' % module_name,
            in_favor_of=class_name,
            remove_in=+2)
        def __init__(self, *args, **kwargs):
            super(Driver, self).__init__(*args, **kwargs)

    return Driver
