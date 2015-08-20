import abc
import functools

import six
import testtools
from testtools import matchers


CURRENT_KEYSTONE_VERSION = 8


def versioned_abstractmethod(added_in=None, removed_in=None):
    def decorator(f):
        if added_in:
            f.__version_added__ = added_in
        if removed_in:
            f.__version_removed__ = removed_in
        return f
    return decorator


class VersionedAPI(abc.ABCMeta):

    def __new__(mcls, name, bases, namespace):
        cls = abc.ABCMeta.__new__(mcls, name, bases, namespace)
        #print super(VersionedAPI, mcls)
        #cls = super(VersionedAPI, mcls).__new__(mcls, name, bases, namespace)

        interface_version = getattr(cls, 'interface_version', None)
        if not interface_version:
            raise TypeError('Interface version not found')

        versioned_methods = set(name for name, value in namespace.items()
                                if hasattr(value, '__version_added__') or
                                    hasattr(value, '__version_removed__'))
        cls.__versioned_methods__ = frozenset(versioned_methods)

        required_version = getattr(cls, 'required_version', None)
        if not required_version:
            return cls

        if required_version > interface_version:
            raise TypeError('Required version is newer than interface version')

        def not_implemented(*args, **kwargs):
            raise NotImplementedError

        required_methods = set()
        for base in bases:
            for name in getattr(base, '__versioned_methods__', []):
                method = getattr(base, name)

                if getattr(method, '__version_added__', 0) > required_version:
                    setattr(cls, name, not_implemented)
                elif getattr(method, '__version_removed__', 0):
                    pass  # maybe we don't actually care
                elif name not in namespace:
                    required_methods.add(name)

        if required_methods:
            print 'R0', cls.__abstractmethods__
            cls.__abstractmethods__ = frozenset(
                cls.__abstractmethods__.union(required_methods))
            print 'R1', cls.__abstractmethods__

        return cls


@six.add_metaclass(VersionedAPI)
class Driver(object):
    interface_version = CURRENT_KEYSTONE_VERSION

    @abc.abstractmethod
    def method1(self):
        pass


class TestCurrentDriver(testtools.TestCase):

    def test_broken_because_it_doesnt_implement_method(self):
        class Impl(Driver):
            required_version = CURRENT_KEYSTONE_VERSION

        self.assertThat(Impl, matchers.raises(TypeError))

    def test_working_impl(self):
        class Impl(Driver):
            required_version = CURRENT_KEYSTONE_VERSION

            def method1(self):
                pass

        Impl()


@six.add_metaclass(VersionedAPI)
class NewDriver(object):
    interface_version = CURRENT_KEYSTONE_VERSION + 1

    @abc.abstractmethod
    def method1(self):
        pass

    @versioned_abstractmethod(added_in=CURRENT_KEYSTONE_VERSION+1)
    def method2(self):
        pass

    @versioned_abstractmethod(removed_in=CURRENT_KEYSTONE_VERSION)
    def method0(self):
        pass


class TestNewDriver(testtools.TestCase):

    def test_old_version_of_implementation_works(self):
        class Impl(NewDriver):
            required_version = CURRENT_KEYSTONE_VERSION

            def method1(self):
                pass

        obj = Impl()
        obj.method1()

    def test_calling_new_method_on_old_dirver_raises_is_not_implemented(self):
        class Impl(NewDriver):
            required_version = CURRENT_KEYSTONE_VERSION

            def method1(self):
                pass

        obj = Impl()
        self.assertThat(obj.method2, matchers.raises(NotImplementedError))

    def test_new_implementation_with_missing_method_breaks(self):
        class Impl(NewDriver):
            required_version = CURRENT_KEYSTONE_VERSION + 1

            def method1(self):
                pass

        self.assertThat(Impl, matchers.raises(TypeError))

    def test_new_implementation_works(self):
        class Impl(NewDriver):
            required_version = CURRENT_KEYSTONE_VERSION + 1

            def method1(self):
                pass

            def method2(self):
                pass

        Impl()

    def test_removed_methods_are_never_required(self):
        # NOTE(dstanek): the assumption is that a method is removed
        # because it is no longer called so there is no reason to
        # enforce its existence even in a version where it was
        # previously required.

        class ImplAtNewVersion(NewDriver):
            required_version = CURRENT_KEYSTONE_VERSION + 1

            def method1(self):
                pass

            def method2(self):
                pass

        print 'YYY', NewDriver.__abstractmethods__
        print 'XXX', ImplAtNewVersion.__abstractmethods__
        print 'XXX', ImplAtNewVersion.method1
        print 'XXX', ImplAtNewVersion.method2

        ImplAtNewVersion()

        class ImplAtOldVersion(NewDriver):
            required_version = CURRENT_KEYSTONE_VERSION

            def method1(self):
                pass

        ImplAtOldVersion()


class TestDriverHeirarchy(testtools.TestCase):

    def test_subsclass_of_a_driver_subclass_with_required_version_in_parent(self):
        class Impl(NewDriver):
            required_version = CURRENT_KEYSTONE_VERSION + 1

        self.assertThat(Impl, matchers.raises(TypeError))

        class ImplImpl(Impl):

            def method1(self):
                pass

            def method2(self):
                pass

        ImplImpl()

    def test_subsclass_of_a_driver_subclass_with_required_version(self):
        class Impl(NewDriver):
            pass  # TODO(dstanek): maybe a test to add more abstract methods?

        self.assertThat(Impl, matchers.raises(TypeError))

        class ImplImpl(Impl):
            required_version = CURRENT_KEYSTONE_VERSION + 1

            def method1(self):
                pass

            def method2(self):
                pass

        ImplImpl()
