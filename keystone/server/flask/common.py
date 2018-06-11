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

from __future__ import absolute_import

import abc
import collections
import six
import sys

from flask import blueprints
import flask_restful


ResourceMap = collections.namedtuple('resource_map', 'resource, urls, kwargs')


def _abstract_property(func):
    # NOTE(morgan): in python3.3+, it is more correct to utilize @property
    # around abstractmethod because it is properly marked as abstract,
    # otherwise use abc.abstractproperty.
    if sys.version_info > (3, 3):
        return property(abc.abstractmethod(func))
    else:
        return abc.abstractproperty(func)


@six.add_metaclass(abc.ABCMeta)
class APIBase(object):
    @_abstract_property
    def _import_name(self):
        """Override with a property set to the value of `__name__`"""
        raise NotImplementedError()

    @_abstract_property
    def resource_mapping(self):
        """Override with a property of a list of ResourceMap named tuples."""
        return []

    @property
    def _url_prefix(self):
        # NOTE(morgan): Keystone only has a V3 API at this time, this is
        # allowed to be overridden in extraordinary circumstances such as
        # the root discovery and/or a future V4 (or other) API.
        return '/'.join(['/v3', self.__url_prefix])

    def __init__(self, name, url_prefix, media_type='application/json'):
        """APIBase object.

        :param name: API name, e.g. `Users`
        :type name: str
        :param url_prefix: Prefix of the URL, e.g. `/users`; /v3 is prepended
            automatically.
        :type url_prefix: str
        :param media_type: default media type to return
        :type media_type: str
        """
        # NOTE(morgan): Keystone only has V3 with exception of the root
        self.__api_name = name
        self.__url_prefix = url_prefix
        self.__blueprint = blueprints.Blueprint(name, self._import_name)
        self.__api_bp = flask_restful.Api(
            self.__blueprint, default_mediatype=media_type, decorators=None,
            errors=None, prefix=self._url_prefix)
        self.__registered = False

    def __assert_not_registered(self):
        # Make sure we are not registered if we are adding resources or
        # performing a registration.
        if self.__registered:
            raise RuntimeError(
                'API %(name)s (%(imp_name)s) is already registered.' %
                    {'name': self.__api_name, 'imp_name': self._import_name})

    def add_resources(self):
        """Adds resources and routes to the API.

        Reading from the :attr:`resource_mapping` attribute, each entry is
        applied to the blueprint_api via :meth:`_add_resource`. This is called
        either directly or via the classmethod :meth:`register_to_flask_app`.

        Each ResourceMap is a :class:`ResourceMap` (named tuple) consising of
        three elements:

            `resource` is a :class:`flask_restful:Resourc`

            `urls` is a list of url routes to match for the resource, standard
            flask routing rules apply.  Any url variables will be passed to
            the resource method as args.

            `kwargs` is a dict, see :meth:`flast_restful.Api.add_resource`
        """
        for entry in self.resource_mapping:
            self._add_resource(entry.resource, *entry.urls, **entry.kwargs)

    def _add_resource(self, resource, *urls, **kwargs):
        """Adds a resource to the api.

        :param resource: the class name of your resource
        :type resource: :class:`flask_restful.Resource`

        :param urls: one or more url routes to match for the resource, standard
                     flask routing rules apply.  Any url variables will be
                     passed to the resource method as args.
        :type urls: str

        :param endpoint: endpoint name (defaults to
            :meth:`flask_restful.Resource.__name__.lower` Can be used to
            reference this route in :class:`fields.Url` fields
        :type endpoint: str

        :param resource_class_args: args to be forwarded to the constructor of
            the resource.
        :type resource_class_args: tuple

        :param resource_class_kwargs: kwargs to be forwarded to the constructor
            of the resource.
        :type resource_class_kwargs: dict

        Additional keyword arguments not specified above will be passed as-is
        to :meth:`flask.Flask.add_url_rule`.

        Examples::

            api._add_resource(HelloWorld, '/', '/hello')
            api._add_resource(Foo, '/foo', endpoint="foo")
            api._add_resource(FooSpecial, '/special/foo', endpoint="foo")

        """
        # Pass through to flask_restful.Api.add_resource, this is to make sure
        # `add_resources` is more readable
        self.__assert_not_registered()
        self.__api_bp.add_resource(resource, *urls, **kwargs)

    def set_registered(self):
        self.__registered = True

    @property
    def blueprint(self):
        # Can be used for direct registration that doesn't utilize the
        # classmethod "register_to_flask_app"
        return self.__api_bp

    @classmethod
    def register_to_flask_app(cls, flask_app, name, url_prefix):
        """APIBase object.

        :param name: API name, e.g. `Users`
        :type name: str
        :param url_prefix: Prefix of the URL, e.g. `/users`; /v3 is prepended
            automatically.
        :type url_prefix: str
        """
        api_instance = cls(name, url_prefix=url_prefix)
        flask_app.register_blueprint(api_instance.blueprint)
        api_instance.set_registered()

