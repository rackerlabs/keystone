#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc
import inspect

import six

from keystone import exception
from keystone.i18n import _


def _assert_method_signature_match(name, cls, base_cls):
    cls_argspec = inspect.getargspec(getattr(cls, name))
    base_argspec = inspect.getargspec(getattr(base_cls, name))
    # TODO(morganfainberg): Support decorated methods. Right now this check
    # will not support decorated methods as they have the argspec of the
    # resulting wrapper. Not all wrapped callables will carry the original
    # argspec.
    if base_argspec != cls_argspec:
        cls_module = inspect.getmodule(cls)
        base_module = inspect.getmodule(base_cls)
        raise MethodSignatureMismatch(method=name,
                                      cls_argspec=cls_argspec,
                                      cls='.'.join([cls_module.__name__,
                                                    cls.__name__]),
                                      base_cls='.'.join([base_module.__name__,
                                                        base_cls.__name__]),
                                      base_argspec=str(base_argspec))


class MethodSignatureMismatch(exception.Error):
    """Exception indicating there was a method signature mismatch."""

    message_format = _('Signature mismatch for "%(cls)s.%(method)s" '
                       'with argspec "%(cls_argspec)s". Defined '
                       'on "%(base_cls)s" as "%(base_argspec)s"')


class StrictABCMeta(abc.ABCMeta):
    def __new__(mcls, name, bases, namespace):
        """Raises if the abstractmethod sig is mismatched from the base."""
        cls = super(StrictABCMeta, mcls).__new__(mcls, name, bases, namespace)
        # Traverse the MRO and look for abstract methods we need to validate
        # signatures against.
        for base in inspect.getmro(cls):
            for name in getattr(base, '__abstractmethods__', set()):
                value = getattr(base, name, None)
                if getattr(value, '__isabstractmethod__', False):
                    # The method is abstract on the current base. Validate that
                    # the method signature matches the signature of the method
                    # defined on the subclass.
                    _assert_method_signature_match(name, cls, base)
        return cls


def abstractclass(cls):
    """Simplified class-decorator to add the StrictABCMeta to a class.

    Usage::

        from keystone.common import strict_abc

        @strict_abc.abstractclass
        class example(object):
            ...
    """
    return six.add_metaclass(StrictABCMeta)(cls)


abstractmethod = abc.abstractmethod
abstractproperty = abc.abstractproperty
