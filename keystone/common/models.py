# Copyright (C) 2011 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base model for keystone internal services

Unless marked otherwise, all fields are strings.

"""
from keystone import exception
from keystone.i18n import _LW
from keystone.openstack.common import log

LOG = log.getLogger(__name__)


class Model(dict):
    """Base model class."""

    def __hash__(self):
        return self['id'].__hash__()

    @property
    def known_keys(self):
        # required_keys and optional_keys are class attributes
        # accessible from the instance
        return (getattr(self, 'required_keys', tuple())
                + getattr(self, 'optional_keys', tuple()))

    def validate(self, only=None, strict=False):
        """Instance level model validation

        :type strict: boolean
        :param strict: whether to raise Validation error
        :type only: iterable
        :param only: restricts validation to attributes provided

        Check if all required attributes present in a model
        Raise exception.ValidationError on incomplete model if strict is True
        """
        missing = set(getattr(self, 'required_keys', tuple()))
        if isinstance(only, (list, tuple, set, dict)):
            missing.intersection_update(only)
        missing.difference_update(self)

        if missing:
            if strict:
                raise exception.ValidationError(
                    attribute=', '.join(missing),
                    target=self.get('id'))
            else:
                LOG.warn(_LW('Expecting to find %(missing)s in %(id)s') % {
                    'missing': ', '.join(missing),
                    'id': self.get('id')
                })
        return self


class Token(Model):
    """Token object.

    Required keys:
        id
        expires (datetime)

    Optional keys:
        user
        tenant
        metadata
        trust_id
    """

    required_keys = ('id', 'expires')
    optional_keys = ('extra',)


class Service(Model):
    """Service object.

    Required keys:
        id
        type
        name

    Optional keys:
    """

    required_keys = ('id', 'type', 'name')
    optional_keys = tuple()


class Endpoint(Model):
    """Endpoint object

    Required keys:
        id
        region
        service_id

    Optional keys:
        internalurl
        publicurl
        adminurl
    """

    required_keys = ('id', 'region', 'service_id')
    optional_keys = ('internalurl', 'publicurl', 'adminurl')


class User(Model):
    """User object.

    Required keys:
        id
        name
        domain_id

    Optional keys:
        password
        description
        email
        enabled (bool, default True)
        default_project_id
    """

    required_keys = ('id', 'name', 'domain_id')
    optional_keys = ('password', 'description', 'email', 'enabled',
                     'default_project_id')


class Group(Model):
    """Group object.

    Required keys:
        id
        name
        domain_id

    Optional keys:

        description

    """

    required_keys = ('id', 'name', 'domain_id')
    optional_keys = ('description',)


class Project(Model):
    """Project object.

    Required keys:
        id
        name
        domain_id

    Optional Keys:
        description
        enabled (bool, default True)

    """

    required_keys = ('id', 'name', 'domain_id')
    optional_keys = ('description', 'enabled')


class Role(Model):
    """Role object.

    Required keys:
        id
        name

    """

    required_keys = ('id', 'name')
    optional_keys = tuple()


class Trust(Model):
    """Trust object.

    Required keys:
        id
        trustor_user_id
        trustee_user_id
        project_id
    """

    required_keys = ('id', 'trustor_user_id', 'trustee_user_id', 'project_id')
    optional_keys = ('expires_at',)


class Domain(Model):
    """Domain object.

    Required keys:
        id
        name

    Optional keys:

        description
        enabled (bool, default True)

    """

    required_keys = ('id', 'name')
    optional_keys = ('description', 'enabled')
