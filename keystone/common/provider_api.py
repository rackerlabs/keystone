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


class ProviderAPIs(object):

    __registry = {}
    __locked = False

    __iter__ = __registry.__iter__
    __getitem__ = __registry.__getitem__

    def __init__(self):
        raise RuntimeError('`ProviderAPIs` class may not be instantiated.')

    @classmethod
    def __getattr__(cls, item):
        try:
            return cls.__registry[item]
        except KeyError:
            raise AttributeError("'ProviderAPIs' has no attribute %s" % item)

    @classmethod
    def _register_provider_api(cls, name, obj):
        """Register an instance of a class as a provider api"""
        if cls.__locked:
            raise RuntimeError(
                'Programming Error: The provider api registry has been '
                'locked (post configuration). Ensure all provider api '
                'managers are instantiated before locking.')

        if name in cls.__registry:
            raise DuplicateProviderError(
                '`%(name)s` has already been registered as an api '
                'provider by `%(prov)r`' % {'name': name,
                                            'prov': cls.__registry[name]})
        cls.__registry[name] = obj

    @classmethod
    def _clear_registry_instances(cls):
        """This is only to ever be used in testing."""
        cls.__registry.clear()
        cls.__locked = False

    @classmethod
    def lock_provider_registry(cls):
        cls.__locked = True


class DuplicateProviderError(Exception):
    """Attempting to register a duplicate API provider."""


class ProviderAPIMixin(object):
    """Allow referencing provider apis on self via __getattr__

    Be sure this class is first in the class definition for inheritance.
    """
    def __getattr__(self, item):
        return getattr(ProviderAPIs, item)
