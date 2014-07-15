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

"""Descriptor objects for the in-memory token data structure."""

import abc
import weakref

from keystoneclient.common import cms
from keystoneclient import utils as ksc_utils
import six
from sqlalchemy import util as sqla_util


from keystone.common import config
from keystone.common import dependency
from keystone import exception
from keystone.openstack.common.gettextutils import _
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log
from keystone.openstack.common import timeutils
from keystone import token


CONF = config.CONF
LOG = log.getLogger(__name__)


class InvalidTokenPrimitive(Exception):
    """An internal-only exception used to indicate a dict was created from
    KeystoneToken.to_primitive method.

    This exception should not ever get exposed outside of the KeystoneToken
    class.
    """


@six.add_metaclass(abc.ABCMeta)
class TokenDescriptor(object):

    def __init__(self, default):
        self.default = default
        self.data = weakref.WeakKeyDictionary()

    def __get__(self, instance, owner):
        if instance is None:
            # NOTE(morganfainberg): If we don't have an instance, this is being
            # called at the class level, we want to in-fact return the self
            # object so we can interact with it directly.
            return self
        return self.data.get(instance, self.default)

    @abc.abstractmethod
    def __set__(self, instance, value):
        self.data[instance] = value

    def to_primitive(self, instance):
        """A descriptor specific method of returning the "primitive".

        Some data types (e.g. trust, user) will only want to store the ID not
        the complete object, this is a class-specific method that is meant to
        be overridden as needed to extract the primitive for the
        KeystoneToken object ``to_primitive`` method.

        :param instance: The instance object that the value should be
                         associated with.
        :return: the primitive based on the value argument
        """
        return self.data[instance]

    def from_primitive(self, instance, value):
        """A descriptor specific method to restore from the "primitive".

        Some data types may have special handling for restoring from the
        primitive value (e.g. ISOTIME strings), which should be handled
        in a different manner than simply issuing a __set__ with the primitive
        value.

        :param instance: Instance the property descriptor is being accessed
                         from
        :param value: the primitive value
        """
        self.__set__(instance, value)


class TokenDescriptorIdPrimitive(TokenDescriptor):
    def to_primitive(self, instance):
        return self.data[instance]['id']


@dependency.requires('trust_api')
class TokenTrust(TokenDescriptorIdPrimitive):
    """Object that does the lookup of the trust ref based on trust_id.

    Behind the scenes, the trust_id is converted to the trust_ref if trusts
    are enabled.
    """
    def __set__(self, instance, value):
        if CONF.trust.enabled:
            self.data[instance] = sqla_util.immutabledict(
                self.trust_api.get_trust(value))


class TokenDatetime(TokenDescriptor):
    def __get__(self, instance, owner):
        """Get the value, if no value is set, set a sane default.

        If the time data has no value yet, set the value, ensure the stored
        value is always ISOTIME format. Return the DATETIME object format
        when accessed.
        """
        if instance is None:
            # NOTE(morganfainberg): If we don't have an instance, this is being
            # called at the class level, we want to in-fact return the self
            # object so we can interact with it directly.
            return self

        timedata = None
        if instance not in self.data:
            if callable(self.default):
                # NOTE(morganfainberg): The default is a callable, call the
                # function instead of using the direct value as the default.
                timedata = self.default()
            else:
                timedata = self.default
            self.data[instance] = timeutils.isotime(timedata, subsecond=True)

        if timedata is None:
            timedata = timeutils.normalize_time(
                timeutils.parse_isotime(self.data[instance]))

        return timedata

    def __set__(self, instance, value):
        # Always serialize the time-format to isotime
        self.data[instance] = timeutils.isotime(value, subsecond=True)

    def from_primitive(self, instance, value):
        # NOTE(morganfainberg): the primitive in this case should always be
        # an ISOTIME string. Since we do serialization/deserialization on these
        # strings during __get__ and __set__ calls, we can simply store the
        # value again, no __set__ serialization logic required.
        self.data[instance] = value


@dependency.requires('assignment_api')
class TokenDomain(TokenDescriptorIdPrimitive):
    """Object that does the lookup of the domain ref based on domain_id.

    Behind the scenes, the domain_id is converted to the filtered domain_ref.
    """
    def __set__(self, instance, value):
        domain_data = self.assignment_api.get_domain(value)
        self.data[instance] = sqla_util.immutabledict(
            {'id': domain_data['id'], 'name': domain_data['name']})


class DomainAwareDescriptorValueDict(dict):
    """This is a domain aware object that acts like a dictionary.

    This object allows for re-use of the Domain descriptor within other
    descriptors such as Project and User.
    """
    domain = TokenDomain(None)

    def __init__(self, *args, **kwargs):
        domain = kwargs.pop('domain', None)
        super(DomainAwareDescriptorValueDict, self).__init__(*args, **kwargs)
        self['domain'] = self.domain
        if domain is not None:
            self.domain = domain

    def __setitem__(self, key, value):
        if key == 'domain':
            self.domain = value
        else:
            super(DomainAwareDescriptorValueDict, self).__setitem__(key, value)


@dependency.requires('assignment_api')
class TokenProject(TokenDescriptorIdPrimitive):
    """Object that does the lookup of the project ref based on project_id.

    Behind the scenes, the project_id is converted to the filtered project_ref.
    """
    def __set__(self, instance, value):
        project_data = self.assignment_api.get_project(value)
        data_obj = DomainAwareDescriptorValueDict(
            id=project_data['id'],
            name=project_data['name'],
            domain=project_data['domain_id'])
        self.data[instance] = sqla_util.immutabledict(data_obj)


@dependency.requires('identity_api')
class TokenUser(TokenDescriptorIdPrimitive):
    """Object that does the lookup of the user ref based on user_id.

    Behind the scenes, the user_id is converted to the filtered user_ref.
    """
    def __set__(self, instance, value):
        user_data = self.identity_api.get_user(value)
        data_obj = DomainAwareDescriptorValueDict(
            id=user_data['id'],
            name=user_data['name'],
            domain=user_data['domain_id'])
        self.data[instance] = sqla_util.immutabledict(data_obj)


@dependency.optional('oauth_api')
class TokenOAuth(TokenDescriptor):
    def __set__(self, instance, value):
        if self.oauth_api:
            oauth_data = self.oauth_api.get_access_token(value)
            self.data[instance] = sqla_util.immutabledict(
                {'access_token_id': oauth_data['id'],
                 'consumer_id': oauth_data['consumer_id'],
                 'role_ids': jsonutils.loads(oauth_data['role_ids'])})


@dependency.requires('assignment_api')
class KeystoneTokenModel(object):
    """The Keystone in-memory token object.

    This object represents the in-memory token object that unifies all token
    versions. The full data set needed to issue, validate, and interact with
    a given token is contained within this object.
    """

    # This value will be used to determine if a dictionary retrieved from a
    # token persistence backend was serialized with the
    # KeystoneToken.to_primitive method. If this key exists and is set to True
    # the backend can/will try and use KeystoneToken.from_primitive() instead
    # of the KeystoneToken.from_serialized_token method.
    primitive_serializer_key = '_TO_PRIMITIVE_FROM_KEYSTONETOKEN'

    expires_at = TokenDatetime(token.default_expire_time)
    issued_at = TokenDatetime(timeutils.utcnow)
    domain = TokenDomain(None)
    project = TokenProject(None)
    oauth = TokenOAuth(None)
    trust = TokenTrust(None)
    user = TokenUser(None)

    # Descriptors that will be converted to primitive values when
    # .to_primitive() is called.
    _to_primitive_attrs = frozenset(['expires_at', 'issued_at', 'domain',
                                     'project', 'oauth', 'trust', 'user'])

    # Attributes that will be included in the primitive dict when
    # .to_primitive() is called. These must be python primitives, and if this
    # is not the case, the attribute should be converted to a descriptor that
    # can handle this conversion.
    _include_in_to_primitive = frozenset(['is_admin', 'includes_catalog',
                                          'token_id', 'short_id', 'bind',
                                          'roles'])

    @ksc_utils.positional(1)
    def __init__(self, token_id, includes_catalog, is_admin):
        self._token_id = token_id
        self._short_id = cms.cms_hash_token(self.token_id,
                                            mode=CONF.token.hash_algorithm)
        self.is_admin = is_admin
        self.includes_catalog = includes_catalog
        self.bind = {}
        self.roles = []
        self.frozen = False

    def __setattr__(self, key, value):
        if self.frozen:
            # NOTE(morganfainberg): Once a token has been issued or if it is
            # loaded from a set of primitives, it is frozen. Nothing should
            # ever change the values of the token after that point.
            raise AttributeError(_('Values of a token cannot be changed once '
                                   'the token has been loaded or issued.'))

        if ((self.project is not None and key == 'domain') or
                (self.domain is not None and key == 'project')):
            raise exception.ValidationError(_('A token cannot be scoped to '
                                              'both a project and domain.'))

        super(KeystoneTokenModel, self).__setattr__(key, value)

    @property
    def short_id(self):
        return self._short_id

    @property
    def token_id(self):
        return self._token_id

    @token_id.setter
    def token_id(self, value):
        self._token_id = value
        self._short_id = cms.cms_hash_token(self.token_id,
                                            mode=CONF.token.hash_algorithm)

    def freeze(self):
        """Mark the token as frozen (cannot be changed).

        This is done automatically when the token is serialized, or if the
        token was loaded either from primitives or a serialized format.

        If the token is already frozen, there is nothing to do.
        """
        if not self.frozen:
            self.frozen = True

    def populate_roles(self):
        """Populate the token roles based upon data that exists in the model.

        This method will perform the heavy lifting of querying the
        assignment_api to determine the roles the token should contain. This
        should be the last action performed before serializing the token or
        marking the token as frozen.

        Calling this method a second time will repopulate the roles which is
        an expensive operation unless the token is marked as frozen. A frozen
        token will ignore requests to repopulate the roles.
        """
        if self.frozen:
            return

        # Handle the OAuth case
        if self.oauth is not None:
            all_roles = self.assignment_api.list_roles()
            # A tuple of immutabledict containing the role_id and role_name
            # of each role in the authorized role list for the OAuth
            # access token.
            self.roles = tuple([sqla_util.immutabledict({'id': x['id'],
                                                         'name': x['name']})
                                for x in all_roles if
                                x['id'] in self.oauth['role_ids']])
            return

        # Handle the non OAuth case
        if self.trust is not None:
            user_id = self.trust['trustor_user_id']
            project_id = self.trust['project_id']
            domain_id = None
        else:
            user_id = self.user['id']
            project_id = self.project['id']
            domain_id = self.domain['id']

        if project_id or domain_id:
            roles = self._get_roles_for_user(user_id=user_id,
                                             domain_id=domain_id,
                                             project_id=project_id)

            filtered_roles = []
            if self.trust is not None:
                trust_roles = set([x['id'] for x in self.trust.roles])
                for role in roles:
                    if role['id'] in trust_roles:
                        filtered_roles.append(
                            sqla_util.immutabledict({'id': role['id'],
                                                     'name': role['name']}))
                    else:
                        raise exception.Forbidden(
                            _('Trustee has no delegated roles.'))
            else:
                filtered_roles = [sqla_util.immutabledict({'id': x['id'],
                                                           'name': x['name']})
                                  for x in roles]

            if not filtered_roles:
                if project_id:
                    msg = _('User %(user_id)s has no access '
                            'to project %(project_id)s') % {
                                'user_id': user_id,
                                'project_id': project_id}
                else:
                    msg = _('User %(user_id)s has no access '
                            'to domain %(domain_id)s') % {
                                'user_id': user_id,
                                'domain_id': domain_id}
                LOG.debug(msg)
                raise exception.Unauthorized(msg)
            self.roles = tuple(filtered_roles)

    @ksc_utils.positional(1)
    def _get_roles_for_user(self, user_id, domain_id, project_id):
        roles = []
        if domain_id:
            roles = self.assignment_api.get_roles_for_user_and_domain(
                user_id, domain_id)
        if project_id:
            roles = self.assignment_api.get_roles_for_user_and_project(
                user_id, project_id)
        return [self.assignment_api.get_role(role_id) for role_id in roles]

    @classmethod
    def from_serialized_token(cls, token_data):
        # TODO(morganfainberg): Consume a serialized token and convert to an
        # instantiation of the KeystoneTokenModel object.
        pass

    def serialize_token(self, formatter):
        self.freeze()
        # TODO(morganfainberg): Serialize the token

    def to_primitive(self):
        """Convert the token to a dictionary of python primitive values.

        The ability to convert the unified token object to a simple set of
        python primitives important when dealing with the token-persistence
        backends as each backend has differing requirements for data formats.
        To ensure no unsupported data types are stored in a given backend, this
        method will convert the token data to a primitive-only format.

        :return: dictionary of python primitive values
        """
        primitives = {}
        for attr in self._to_primitive_attrs:
            primitives[attr] = getattr(
                KeystoneTokenModel, attr).to_primitive(self)
        for attr in self._include_in_to_primitive:
            primitives[attr] = getattr(self, attr)
        # Indicate this was a serialization from the
        primitives[self.primitive_serializer_key] = True
        return primitives


    @classmethod
    def from_primitive(cls, primitive_token_fmt):
        """Convert the token from the primitive format back to the object.

        This method is the inverse of the ``to_primitive`` method, which will
        convert the primitive token data back to the in-memory object format.

        :param primitive_token_fmt: dictionary of python primitives that can
                                    be converted to a full token object
        :return: instantiated KeystoneToken object
        """
        if not isinstance(primitive_token_fmt, dict):
            raise exception.ValidationError(
                _('Primitive "%r" is not a dict.') % primitive_token_fmt)

        if cls.primitive_serializer_key not in primitive_token_fmt:
            raise InvalidTokenPrimitive()

        token_obj = KeystoneTokenModel(
            token_id=primitive_token_fmt['token_id'],
            includes_catalog=primitive_token_fmt['includes_catalog'],
            is_admin=primitive_token_fmt['is_admin'])
        token_obj.bind = primitive_token_fmt['bind']
        token_obj.roles = primitive_token_fmt['roles']
        for attr in KeystoneTokenModel._to_primitive_attrs:
            value = primitive_token_fmt.get(attr)
            if value is not None:
                getattr(KeystoneTokenModel, attr).from_primitive(token_obj,
                                                                 value)
        token_obj.freeze()
        return token_obj
