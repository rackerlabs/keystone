# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

REGISTRY = {}


class UnresolvableDependencyException(Exception):
    def __init__(self, name):
        msg = 'Unregistered dependency: %s' % name
        super(UnresolvableDependencyException, self).__init__(msg)


def provider(name):
    """Register the wrapped dependency provider under the specified name."""
    def wrapper(cls):
        def wrapped(init):
            def __wrapped_init__(self, *args, **kwargs):
                """Initialize the wrapped object and add it to the registry."""
                init(self, *args, **kwargs)
                REGISTRY[name] = self

            return __wrapped_init__

        cls.__init__ = wrapped(cls.__init__)
        return cls

    return wrapper


def requires(*dependencies):
    """Inject specified dependencies from the registry into the instance.

    For a dependency 'dep_api' creates a class level function:
      - cls.get_dep_api()
    and a instance level property
      - self.dep_api

    On class init it will also guarantee that all dependencies are met
    """

    def class_prop(name):
        @classmethod
        def func(cls):
            try:
                return REGISTRY[name]
            except KeyError:
                raise UnresolvableDependencyException(name)

        return func

    def inst_prop(name):
        @property
        def func(self):
            return getattr(self, name)()
        return func

    def wrap_init(init):
        # this is not really needed except for consistency with the old way
        def __wrapped_init__(self, *args, **kwargs):
            for dep in dependencies:
                getattr(self, dep)

            init(self, *args, **kwargs)

        return __wrapped_init__

    def wrapped(cls):
        for dep in dependencies:
            name = 'get_%s' % dep
            setattr(cls, name, class_prop(dep))
            setattr(cls, dep, inst_prop(name))

        cls.__init__ = wrap_init(cls.__init__)
        return cls

    return wrapped
