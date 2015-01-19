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

import six
import uuid

from keystone.common import strict_abc
from keystone import tests


@six.add_metaclass(strict_abc.StrictABCMeta)
class _StrictABCTestBaseClass(object):
    """A Test class that has the StrictABCMeta class as a Metaclass."""


@strict_abc.abstractclass
class _HelperDecoratorStrictABCTestBaseClass(object):
    """A class that has the StrictABCMeta applied via the helper decorator."""


def _class_factory(name, baseclass=_StrictABCTestBaseClass, method=None):
    if method is None:
        def method_with_known_sig(self, arg1, arg2, kwarg='default'):
            pass

        method = strict_abc.abstractmethod(method_with_known_sig)
    return type(name, (baseclass,), {'method_with_known_signature': method})


class TestStrictABC(tests.TestCase):

    abstract_base_class = _StrictABCTestBaseClass

    def test_strict_abc_method_signature_matches(self):
        """Test classes based on StrictABC with matching signatures.

        Test that ensures a class that extends _StrictABCTestBaseClass with
        overridden method succeeds with matching signatures.

        """
        def override_method(self, arg1, arg2, kwarg='default'):
            pass

        base_cls = _class_factory(uuid.uuid4().hex,
                                  baseclass=self.abstract_base_class)
        _class_factory('WorkingClass', baseclass=base_cls,
                       method=override_method)

    def test_strict_abc_method_signature_mismatch(self):
        """Test classes based on StrictABC with mismatching signatures.

        Test that ensures a class that extends _StrictABCTestBaseClass with
        overridden method fails with mismatching signatures.

        """
        def override_method(self, arg1, arg2):
            pass

        base_cls = _class_factory(uuid.uuid4().hex,
                                  baseclass=self.abstract_base_class)
        self.assertRaises(strict_abc.MethodSignatureMismatch, _class_factory,
                          'NonWorkingClass', baseclass=base_cls,
                          method=override_method)

    def test_strict_abc_subclass_signature_matches(self):
        """Test subclasses based on StrictABC with matching signatures.

        Define a class based upon a class that is based upon the StrictABC
        metaclass that will succeed with an overidden method that has a
        matching signature.

        """
        def method(self, arg1, arg2, kwarg='default'):
            pass

        def subclass_method(self, arg1, arg2, kwarg='default'):
            pass

        base_cls = _class_factory(uuid.uuid4().hex,
                                  baseclass=self.abstract_base_class)
        base_cls = _class_factory('ASubClass', baseclass=base_cls,
                                  method=method)
        _class_factory('WorkingSubSubClass', baseclass=base_cls,
                       method=subclass_method)

    def test_strict_abc_subclass_signature_mismatch(self):
        """Test subclasses based on StrictABC with mismatching signatures.

        Define a class based upon a class that is based upon the StrictABC
        metaclass that will fail with an overidden method that has a
        mismatched signature.

        """
        def method(self, arg1, arg2, kwarg='default'):
            pass

        def subclass_method(self, arg1, kwarg='default'):
            pass

        base_cls = _class_factory(uuid.uuid4().hex,
                                  baseclass=self.abstract_base_class)
        base_cls = _class_factory('SubClass', baseclass=base_cls,
                                  method=method)
        self.assertRaises(strict_abc.MethodSignatureMismatch, _class_factory,
                          'NonWorkingSubSubClass', baseclass=base_cls,
                          method=subclass_method)


class TestHelperDecoratorStrictABC(TestStrictABC):

    abstract_base_class = _HelperDecoratorStrictABCTestBaseClass
