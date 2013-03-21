# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

"""Extensions supporting delegated auth."""

import datetime
import json
import urllib

from keystone.common import controller
from keystone.common import dependency
from keystone.common import extension
from keystone.common import logging
from keystone.common import manager
from keystone.common import oauth
from keystone.common import wsgi
from keystone import config
from keystone import exception


CONF = config.CONF
LOG = logging.getLogger(__name__)
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

EXTENSION_DATA = {
    'name': 'OpenStack OAUTH1 API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-OAUTH1/v1.0',
    'alias': 'OS-OAUTH1',
    'updated': '2013-07-07T12:00:0-00:00',
    'description': 'OpenStack OAuth 1.0A Delegated Auth Mechanism.',
    'links': [
        {
            'rel': 'describedby',
            # TODO(dolph): link needs to be revised after
            #              bug 928059 merges
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api',
        }
    ]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)
extension.register_public_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


def filter_consumer(consumer_ref):
    """Filter out private items in a consumer dict.

    'consumer_secret' is never returned.

    :returns: consumer_ref

    """
    if consumer_ref:
        consumer_ref = consumer_ref.copy()
        consumer_ref.pop('consumer_secret', None)
    return consumer_ref


def filter_token(access_token_ref):
    """Filter out private items in an access token dict.

    'access_secret' is never returned.

    :returns: access_token_ref

    """
    if access_token_ref:
        access_token_ref = access_token_ref.copy()
        access_token_ref.pop('access_secret', None)
    return access_token_ref


def rebuild_url_from_environ(environ):
    url = environ['wsgi.url_scheme'] + '://'
    url += environ['HTTP_HOST']

    if environ.get('RAW_PATH_INFO'):
        url += urllib.quote(environ.get('RAW_PATH_INFO', ''))
    else:
        url += urllib.quote(environ.get('PATH_INFO', ''))
    return url


@dependency.provider('oauth_api')
class Manager(manager.Manager):
    """Default pivot point for the delegated auth credentials backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.oauth.driver)


class DelegatedAuthExtension(wsgi.ExtensionRouter):
    """API Endpoints for the Delegated Auth extension.

    The goal of this extension is to allow third-party service providers
    to acquire tokens with a limited subset of a user's roles for acting
    on behalf of that user. This is done using an oauth-similar flow and
    api.

    The API looks like:

      # Basic admin-only consumer crud
      POST /OS-OAUTH1/consumers
      GET /OS-OAUTH1/consumers
      PATCH /OS-OAUTH1/consumers/$consumer_id
      GET /OS-OAUTH1/consumers/$consumer_id
      DELETE /OS-OAUTH1/consumers/$consumer_id

      # User access token crud
      GET /users/$user_id/OS-OAUTH1/access_tokens
      GET /users/$user_id/OS-OAUTH1/access_tokens/$access_token_id
      GET /users/{user_id}/OS-OAUTH1/access_tokens/{access_token_id}/roles
      GET /users/{user_id}/OS-OAUTH1/access_tokens
          /{access_token_id}/roles/{role_id}
      DELETE /users/$user_id/OS-OAUTH1/access_tokens/$access_token_id

      # OAuth interfaces
      GET /OS-OAUTH1/request_token  # create a request token
      PUT /OS-OAUTH1/authorize  # authorize a request token
      GET /OS-OAUTH1/access_token  # create an access token

    """

    def add_routes(self, mapper):
        consumer_controller = ConsumerCrudV3()
        access_token_controller = AccessTokenCrudV3()
        access_token_roles_controller = AccessTokenRolesV3()
        oauth_controller = OAuthControllerV3()

        # basic admin-only consumer crud
        mapper.connect(
            '/OS-OAUTH1/consumers',
            controller=consumer_controller,
            action='create_consumer',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/OS-OAUTH1/consumers/{consumer_id}',
            controller=consumer_controller,
            action='get_consumer',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-OAUTH1/consumers/{consumer_id}',
            controller=consumer_controller,
            action='update_consumer',
            conditions=dict(method=['PATCH']))
        mapper.connect(
            '/OS-OAUTH1/consumers/{consumer_id}',
            controller=consumer_controller,
            action='delete_consumer',
            conditions=dict(method=['DELETE']))
        mapper.connect(
            '/OS-OAUTH1/consumers',
            controller=consumer_controller,
            action='list_consumers',
            conditions=dict(method=['GET']))

        # user accesss token crud
        mapper.connect(
            '/users/{user_id}/OS-OAUTH1/access_tokens',
            controller=access_token_controller,
            action='list_access_tokens',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/OS-OAUTH1/access_tokens/{access_token_id}',
            controller=access_token_controller,
            action='get_access_token',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/OS-OAUTH1/access_tokens/{access_token_id}',
            controller=access_token_controller,
            action='delete_access_token',
            conditions=dict(method=['DELETE']))
        mapper.connect(
            '/users/{user_id}/OS-OAUTH1/access_tokens/{access_token_id}/roles',
            controller=access_token_roles_controller,
            action='list_access_token_roles',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/OS-OAUTH1/access_tokens/'
            '{access_token_id}/roles/{role_id}',
            controller=access_token_roles_controller,
            action='get_access_token_role',
            conditions=dict(method=['GET']))

        # oauth flow calls
        mapper.connect(
            '/OS-OAUTH1/request_token',
            controller=oauth_controller,
            action='create_request_token',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-OAUTH1/access_token',
            controller=oauth_controller,
            action='create_access_token',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-OAUTH1/authorize/{request_token_id}',
            controller=oauth_controller,
            action='authorize',
            conditions=dict(method=['PUT']))


@dependency.requires('oauth_api', 'token_api')
class ConsumerCrudV3(controller.V3Controller):
    collection_name = 'consumers'
    member_name = 'consumer'

    def create_consumer(self, context, consumer):
        ref = self._assign_unique_id(self._normalize_dict(consumer))
        consumer_ref = self.oauth_api.create_consumer(ref)
        return ConsumerCrudV3.wrap_member(context, consumer_ref)

    def update_consumer(self, context, consumer_id, consumer):
        self._require_matching_id(consumer_id, consumer)
        ref = self._normalize_dict(consumer)
        self._validate_consumer_ref(consumer)
        ref = self.oauth_api.update_consumer(consumer_id, consumer)
        return ConsumerCrudV3.wrap_member(context, ref)

    def list_consumers(self, context):
        ref = self.oauth_api.list_consumers()
        return ConsumerCrudV3.wrap_collection(context, ref)

    def get_consumer(self, context, consumer_id):
        ref = self.oauth_api.get_consumer(consumer_id)
        return ConsumerCrudV3.wrap_member(context, ref)

    def delete_consumer(self, context, consumer_id):
        user_token_ref = self.token_api.get_token(context['token_id'])
        user_id = user_token_ref['user'].get('id')
        self.token_api.delete_tokens(user_id, consumer_id=consumer_id)
        self.oauth_api.delete_consumer(consumer_id)

    def _validate_consumer_ref(self, consumer):
        if 'consumer_secret' in consumer:
            raise exception.ValidationError('Cannot change consumer_secret')


@dependency.requires('oauth_api')
class AccessTokenCrudV3(controller.V3Controller):
    collection_name = 'access_tokens'
    member_name = 'access_token'

    def get_access_token(self, context, user_id, access_token_id):
        access_token = self.oauth_api.get_access_token(access_token_id)
        if access_token['authorizing_user_id'] != user_id:
            raise exception.Unauthorized(_('User IDs do not match'))
        access_token = self._format_token_entity(access_token)
        return AccessTokenCrudV3.wrap_member(context, access_token)

    def list_access_tokens(self, context, user_id):
        refs = self.oauth_api.list_access_tokens(user_id)
        formatted_refs = ([self._format_token_entity(x) for x in refs])
        return AccessTokenCrudV3.wrap_collection(context, formatted_refs)

    def delete_access_token(self, context, user_id, access_token_id):
        access_token = self.oauth_api.get_access_token(access_token_id)
        consumer_id = access_token['consumer_id']
        self.token_api.delete_tokens(user_id, consumer_id=consumer_id)
        return self.oauth_api.delete_access_token(
            user_id, access_token_id)

    def _format_token_entity(self, entity):

        formatted_entity = entity.copy()
        access_token_id = ""
        user_id = ""
        if 'id' in entity:
            access_token_id = formatted_entity['id']
        if 'requested_roles' in entity:
            formatted_entity.pop('requested_roles')
        if 'access_secret' in entity:
            formatted_entity.pop('access_secret')
        if 'authorizing_user_id' in entity:
            user_id = formatted_entity['authorizing_user_id']

        formatted_entity.setdefault('links', {})
        formatted_entity['links']['roles'] = (
            self.base_url('/users/%s/OS-OAUTH1/access_tokens/%s/roles'
                          % (user_id, access_token_id)))

        return formatted_entity


@dependency.requires('oauth_api')
class AccessTokenRolesV3(controller.V3Controller):
    collection_name = 'roles'
    member_name = 'role'

    def list_access_token_roles(self, context, user_id, access_token_id):
        access_token = self.oauth_api.get_access_token(access_token_id)
        if access_token['authorizing_user_id'] != user_id:
            raise exception.Unauthorized(_('User IDs do not match'))
        roles = access_token['requested_roles']
        roles_refs = json.loads(roles)
        formatted_refs = ([self._format_role_entity(x) for x in roles_refs])
        return AccessTokenRolesV3.wrap_collection(context, formatted_refs)

    def get_access_token_role(self, context, user_id,
                              access_token_id, role_id):
        access_token = self.oauth_api.get_access_token(access_token_id)
        if access_token['authorizing_user_id'] != user_id:
            raise exception.Unauthorized(_('User IDs do not match'))
        roles = access_token['requested_roles']
        roles_dict = json.loads(roles)
        for role in roles_dict:
            if role['id'] == role_id:
                role = self._format_role_entity(role)
                return AccessTokenRolesV3.wrap_member(context, role)
        raise exception.RoleNotFound(_('Could not find role'))

    def _format_role_entity(self, entity):

        formatted_entity = entity.copy()
        if 'description' in entity:
            formatted_entity.pop('description')
        if 'enabled' in entity:
            formatted_entity.pop('enabled')
        return formatted_entity


@dependency.requires('oauth_api', 'token_api', 'identity_api',
                     'token_provider_api', 'assignment_api')
class OAuthControllerV3(controller.V3Controller):
    collection_name = 'not_used'
    member_name = 'not_used'

    def create_request_token(self, context):
        request = context['request']
        consumer_id = request.GET.get('oauth_consumer_key')
        requested_role_ids = request.GET.get('requested_role_ids')
        requested_project_id = request.GET.get('requested_project_id')
        if not consumer_id:
            raise exception.ValidationError(
                attribute='oauth_consumer_key', target='request')
        if not requested_role_ids:
            raise exception.ValidationError(
                attribute='requested_role_ids', target='request')
        if not requested_project_id:
            raise exception.ValidationError(
                attribute='requested_project_id', target='request')

        req_role_ids = requested_role_ids.split(',')
        consumer_ref = self.oauth_api._get_consumer(consumer_id)
        consumer = oauth.Consumer(key=consumer_ref['id'],
                                  secret=consumer_ref['consumer_secret'])

        url = rebuild_url_from_environ(request.environ)
        oauth_request = oauth.Request.from_request(
            http_method='GET',
            http_url=url,
            headers=request.headers,
            query_string=request.query_string)
        oauth_server = oauth.Server()
        oauth_server.add_signature_method(oauth.SignatureMethod_HMAC_SHA1())
        params = oauth_server.verify_request(oauth_request,
                                             consumer,
                                             token=None)

        project_params = params['requested_project_id']
        if project_params != requested_project_id:
            msg = _('Non-oauth parameter - project, do not match')
            raise exception.Unauthorized(message=msg)

        roles_params = params['requested_role_ids']
        roles_params_list = roles_params.split(',')
        if roles_params_list != req_role_ids:
            msg = _('Non-oauth parameter - roles, do not match')
            raise exception.Unauthorized(message=msg)

        req_role_list = list()
        all_roles = self.identity_api.list_roles()
        for role in all_roles:
            for req_role in req_role_ids:
                if role['id'] == req_role:
                    req_role_list.append(role)

        if len(req_role_list) == 0:
            msg = _('could not find matching roles for provided role ids')
            raise exception.Unauthorized(message=msg)

        json_roles = json.dumps(req_role_list)
        request_token_duration = CONF.oauth.request_token_duration
        token_ref = self.oauth_api.create_request_token(consumer_id,
                                                        json_roles,
                                                        requested_project_id,
                                                        request_token_duration)

        result = ('oauth_token=%s&oauth_token_secret=%s'
                  % (token_ref['id'], token_ref['request_secret']))

        if CONF.oauth.request_token_duration:
            expiry_bit = '&oauth_expires_at=%s' % token_ref['expires_at']
            result += expiry_bit

        return result

    def create_access_token(self, context):
        request = context['request']
        consumer_id = request.GET.get('oauth_consumer_key')
        request_token_id = request.GET.get('oauth_token')
        oauth_verifier = request.GET.get('oauth_verifier')

        if not consumer_id:
            raise exception.ValidationError(
                attribute='oauth_consumer_key', target='request')
        if not request_token_id:
            raise exception.ValidationError(
                attribute='oauth_token', target='request')
        if not oauth_verifier:
            raise exception.ValidationError(
                attribute='oauth_verifier', target='request')

        consumer = self.oauth_api._get_consumer(consumer_id)
        req_token = self.oauth_api.get_request_token(
            request_token_id)

        expires_at = req_token['expires_at']
        if expires_at:
            now = datetime.datetime.utcnow()
            expires = datetime.datetime.strptime(expires_at, TIME_FORMAT)
            if now > expires:
                raise exception.Unauthorized(_('Request token is expired'))

        consumer_obj = oauth.Consumer(key=consumer['id'],
                                      secret=consumer['consumer_secret'])
        req_token_obj = oauth.Token(key=req_token['id'],
                                    secret=req_token['request_secret'])
        req_token_obj.set_verifier(oauth_verifier)

        url = rebuild_url_from_environ(request.environ)
        oauth_request = oauth.Request.from_request(
            http_method='GET',
            http_url=url,
            headers=request.headers,
            query_string=request.query_string)
        oauth_server = oauth.Server()
        oauth_server.add_signature_method(oauth.SignatureMethod_HMAC_SHA1())
        params = oauth_server.verify_request(oauth_request,
                                             consumer_obj,
                                             token=req_token_obj)

        if len(params) != 0:
            msg = _('There should not be any non-oauth parameters')
            raise exception.Unauthorized(message=msg)

        if req_token['consumer_id'] != consumer_id:
            msg = _('provided consumer key does not match stored consumer key')
            raise exception.Unauthorized(message=msg)

        if req_token['verifier'] != oauth_verifier:
            msg = _('provided verifier does not match stored verifier')
            raise exception.Unauthorized(message=msg)

        if req_token['id'] != request_token_id:
            msg = _('provided request key does not match stored request key')
            raise exception.Unauthorized(message=msg)

        if not req_token.get('authorizing_user_id'):
            msg = _('Request Token does not have an authorizing user id')
            raise exception.Unauthorized(message=msg)

        access_token_duration = CONF.oauth.access_token_duration
        token_ref = self.oauth_api.create_access_token(request_token_id,
                                                       access_token_duration)

        result = ('oauth_token=%s&oauth_token_secret=%s'
                  % (token_ref['id'], token_ref['access_secret']))

        if CONF.oauth.access_token_duration:
            expiry_bit = '&oauth_expires_at=%s' % (token_ref['expires_at'])
            result += expiry_bit

        return result

    def authorize(self, context, request_token_id):
        """An authenticated user is going to authorize a request token.

        As a security precaution, the requested roles must match those in
        the request token. Because this is in a CLI-only world at the moment,
        there is not another easy way to make sure the user knows which roles
        are being requested before authorizing.
        """

        req_token = self.oauth_api.get_request_token(request_token_id)

        expires_at = req_token['expires_at']
        if expires_at:
            now = datetime.datetime.utcnow()
            expires = datetime.datetime.strptime(expires_at, TIME_FORMAT)
            if now > expires:
                raise exception.Unauthorized(_('Request token is expired'))

        req_roles = req_token['requested_roles']
        req_roles_list = json.loads(req_roles)

        req_set = set()
        for x in req_roles_list:
            req_set.add(x['id'])

        # verify the authorizing user has the roles
        user_token = self.token_api.get_token(token_id=context['token_id'])
        credentials = user_token['metadata'].copy()
        user_roles = credentials.get('roles')
        user_id = user_token['user'].get('id')
        cred_set = set(user_roles)

        if not cred_set.issuperset(req_set):
            msg = _('authorizing user does not have role required')
            raise exception.Unauthorized(message=msg)

        # verify the user has the project too
        req_project_id = req_token['requested_project_id']
        user_projects = self.assignment_api.list_user_projects(user_id)
        found = False
        for user_project in user_projects:
            if user_project['id'] == req_project_id:
                found = True
                break
        if not found:
            msg = _("User is not a member of the requested project")
            raise exception.Unauthorized(message=msg)

        # finally authorize the token
        authed_token = self.oauth_api.authorize_request_token(
            request_token_id, user_id)

        to_return = {'token': {'oauth_verifier': authed_token['verifier']}}
        return to_return


class Driver(object):
    """Interface description for a delegated auth driver."""

    def create_consumer(self, consumer_ref):
        """Create consumer.

        :param consumer_ref: consumer ref with consumer name
        :type consumer_ref: dict
        :returns: consumer_ref

        """
        raise exception.NotImplemented()

    def update_consumer(self, consumer_id, consumer_ref):
        """Update consumer.

        :param consumer_id: id of consumer to update
        :type consumer_ref: string
        :param consumer_ref: new consumer ref with consumer name
        :type consumer_ref: dict
        :returns: consumer_ref

        """
        raise exception.NotImplemented()

    def list_consumers(self):
        """List consumers.

        returns: list of consumers

        """
        raise exception.NotImplemented()

    def get_consumer(self, consumer_id):
        """Get consumer.

        :param consumer_id: id of consumer to get
        :type consumer_ref: string
        :returns: consumer_ref

        """
        raise exception.NotImplemented()

    def delete_consumer(self, consumer_id):
        """Delete consumer.

        :param consumer_id: id of consumer to get
        :type consumer_ref: string
        :returns: None.

        """
        raise exception.NotImplemented()

    def list_access_tokens(self, user_id):
        """List access tokens.

        :param user_id: search for access tokens authorized by given user id
        :type user_id: string
        returns: list of access tokens the user has authorized

        """
        raise exception.NotImplemented()

    def delete_access_token(self, user_id, access_token_id):
        """Delete access token.

        :param user_id: authorizing user id
        :type user_id: string
        :param access_token_id: access token to delete
        :type access_token_id: string
        returns: None

        """
        raise exception.NotImplemented()

    def create_request_token(self, consumer_id, requested_roles,
                             requested_project, request_token_duration):
        """Create request token.

        :param consumer_id: the id of the consumer
        :type consumer_id: string
        :param requested_roles: requested roles
        :type requested_roles: string
        :param requested_project_id: requested project id
        :type requested_project_id: string
        :param request_token_duration: duration of request token
        :type request_token_duration: string
        returns: request_token_ref

        """
        raise exception.NotImplemented()

    def get_request_token(self, request_token_id):
        """Get request token.

        :param request_token_id: the id of the request token
        :type request_token_id: string
        returns: request_token_ref

        """
        raise exception.NotImplemented()

    def get_access_token(self, access_token_id):
        """Get access token.

        :param access_token_id: the id of the access token
        :type access_token_id: string
        returns: access_token_ref

        """
        raise exception.NotImplemented()

    def authorize_request_token(self, request_id, user_id):
        """Authorize request token.

        :param request_id: the id of the request token, to be authorized
        :type request_id: string
        :param user_id: the id of the authorizing user
        :type user_id: string
        returns: verifier

        """
        raise exception.NotImplemented()

    def create_access_token(self, request_id, access_token_duration):
        """Create access token.

        :param request_id: the id of the request token, to be deleted
        :type request_id: string
        :param access_token_duration: duration of an access token
        :type access_token_duration: string
        returns: access_token_ref

        """
        raise exception.NotImplemented()
