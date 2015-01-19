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

from keystone import exception
from keystone.i18n import _
from keystone.openstack.common import log


LOG = log.getLogger(__name__)
_VALIDATED_CLASSES = set()


def _assert_method_signature_match(name, cls, base_cls):
    cls_argspec = inspect.getargspec(getattr(cls, name))
    base_argspec = inspect.getargspec(getattr(base_cls, name))
    # TODO(morganfainberg): Support decorated methods. Right now this check
    # will not support decorated methods as they have the argspec of the
    # resulting wrapper. Not all wrapped callables will carry the original
    # argspec.
    if base_argspec != cls_argspec:
        raise MethodSignatureMismatch(method=name,
                                      cls_argspec=cls_argspec,
                                      cls=cls.__name__,
                                      base_cls=base_cls.__name__,
                                      base_argspec=base_argspec)


class MethodSignatureMismatch(exception.Error):
    """Exception indicating there was a method signature mismatch."""

    message_format = _('Method signature mismatch for "%(method)s" with '
                       'argspec "%(cls_argspec)" on "%(cls)s". Defined on '
                       '"%(base_cls)s" as "%(base_argspec)s"')


class StrictABCMeta(abc.ABCMeta):
    def __new__(mcls, name, bases, namespace):
        """Raises if the abstractmethod sig is mismatched from the base."""
        cls = super(StrictABCMeta, mcls).__new__(mcls, name, bases, namespace)
        if cls not in _VALIDATED_CLASSES:
            for base in bases:
                for name in getattr(base, "__abstractmethods__", set()):
                    value = getattr(cls, name, None)
                    if getattr(value, "__isabstractmethod__", False):
                        # This is not an abstract method and is abstract on the
                        # current base. Ensure the signature matches. This will
                        # traverse the entire tree.
                        _assert_method_signature_match(name, cls, base)
            # This validation is only needed on the first attempt to
            # instantiate, add the class to the validated list for future
            # skipping of the validation step.
            _VALIDATED_CLASSES.add(cls)
