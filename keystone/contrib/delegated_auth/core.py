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
      PUT /OS-OAUTH1/consumers/$consumer_id
      GET /OS-OAUTH1/consumers/$consumer_id
      DELETE /OS-OAUTH1/consumers/$consumer_id

      # User access token crud
      GET /users/$user_id/OS-OAUTH1/authorizations
      DELETE /users/$user_id/OS-OAUTH1/authorizations/$access_token

      # Public interface for third-party
      GET /OS-OAUTH1/authenticate  # request a keystone token using an
                                         # access token

      # Public oauth interface for third-party
      GET /OS-OAUTH1/request_token  # get a request token for user to authz
      GET /OS-OAUTH1/access_token  # get an access token when a request
                               #  token has has been authorized

      # Public oauth interface for user
      POST /OS-OAUTH1/authorize  # authorize a request token

    """

    def add_routes(self, mapper):
        consumer_controller = ConsumerCrudV3()
        access_token_controller = AccessTokenCrudV3()
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
            action='delete_access_token',
            conditions=dict(method=['DELETE']))

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
            '/OS-OAUTH1/authorize/{request_key}',
            controller=oauth_controller,
            action='authorize',
            conditions=dict(method=['POST']))


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
        if 'consumer_key' in consumer:
            raise exception.ValidationError('Cannot change consumer_key')
        if 'consumer_secret' in consumer:
            raise exception.ValidationError('Cannot change consumer_secret')


@dependency.requires('oauth_api')
class AccessTokenCrudV3(controller.V3Controller):
    collection_name = 'access_tokens'
    member_name = 'access_token'

    def list_access_tokens(self, context, user_id):
        refs = self.oauth_api.list_access_tokens(user_id)
        return AccessTokenCrudV3.wrap_collection(context, refs)

    def delete_access_token(self, context, user_id, access_token_id):
        access_token = self.oauth_api.get_access_token(access_token_id)
        consumer_id = access_token['consumer_key']
        self.token_api.delete_tokens(user_id, consumer_id=consumer_id)
        return self.oauth_api.delete_access_token(
            user_id, access_token_id)


@dependency.requires('oauth_api', 'token_api', 'identity_api',
                     'token_provider_api', 'assignment_api')
class OAuthControllerV3(controller.V3Controller):
    collection_name = 'not_used'
    member_name = 'not_used'

    def create_request_token(self, context):
        request = context['request']
        consumer_key = request.GET.get('oauth_consumer_key')
        requested_role_ids = request.GET.get('requested_role_ids')
        requested_project_id = request.GET.get('requested_project_id')
        if not consumer_key:
            raise exception.ValidationError(
                attribute='oauth_consumer_key', target='request')
        if not requested_role_ids:
            raise exception.ValidationError(
                attribute='requested_role_ids', target='request')
        if not requested_project_id:
            raise exception.ValidationError(
                attribute='requested_project_id', target='request')

        req_role_ids = requested_role_ids.split(',')
        consumer_ref = self.oauth_api._get_consumer(consumer_key)
        consumer = oauth.Consumer(key=consumer_ref['consumer_key'],
                                  secret=consumer_ref['consumer_secret'])

        url = self._rebuild_url_from_environ(request.environ)
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
        request_token_expiry = CONF.oauth.request_token_expiry
        token_ref = self.oauth_api.create_request_token(consumer_key,
                                                        json_roles,
                                                        requested_project_id,
                                                        request_token_expiry)

        result = ('oauth_token=%s&oauth_token_secret=%s&oauth_expires_at=%s'
                  % (token_ref['request_key'],
                     token_ref['request_secret'],
                     token_ref['expires_at']))

        return result

    def create_access_token(self, context):
        request = context['request']
        consumer_key = request.GET.get('oauth_consumer_key')
        request_token_key = request.GET.get('oauth_token')
        oauth_verifier = request.GET.get('oauth_verifier')

        if not consumer_key:
            raise exception.ValidationError(
                attribute='oauth_consumer_key', target='request')
        if not request_token_key:
            raise exception.ValidationError(
                attribute='oauth_token', target='request')
        if not oauth_verifier:
            raise exception.ValidationError(
                attribute='oauth_verifier', target='request')

        consumer = self.oauth_api._get_consumer(consumer_key)
        req_token = self.oauth_api.get_request_token(
            request_token_key)

        # fix expires
        # check to see if it's expired
        #now = datetime.datetime.utcnow()
        #req_expires_at = req_token['expires_at']
        #req_expires = datetime.datetime.strptime(req_expires_at, TIME_FORMAT)
        #if now > req_expires:
            #raise exception.Unauthorized(_('Request token is expired'))

        consumer_obj = oauth.Consumer(key=consumer['consumer_key'],
                                      secret=consumer['consumer_secret'])
        req_token_obj = oauth.Token(key=req_token['request_key'],
                                    secret=req_token['request_secret'])
        req_token_obj.set_verifier(oauth_verifier)

        url = self._rebuild_url_from_environ(request.environ)
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

        if req_token['consumer_key'] != consumer_key:
            msg = _('provided consumer key does not match stored consumer key')
            raise exception.Unauthorized(message=msg)

        if req_token['verifier'] != oauth_verifier:
            msg = _('provided verifier does not match stored verifier')
            raise exception.Unauthorized(message=msg)

        if req_token['request_key'] != request_token_key:
            msg = _('provided request key does not match stored request key')
            raise exception.Unauthorized(message=msg)

        if not req_token.get('authorizing_user_id'):
            msg = _('Request Token does not have an authorizing user id')
            raise exception.Unauthorized(message=msg)

        access_token_expiry = CONF.oauth.access_token_expiry

        token_ref = self.oauth_api.create_access_token(request_token_key,
                                                       access_token_expiry)

        result = ('oauth_token=%s&oauth_token_secret=%s&oauth_expires_at=%s'
                  % (token_ref['access_key'],
                     token_ref['access_secret'],
                     token_ref['expires_at']))

        return result

    def authorize(self, context, request_key):
        """An authenticated user is going to authorize a request token.

        As a security precaution, the requested roles must match those in
        the request token. Because this is in a CLI-only world at the moment,
        there is not another easy way to make sure the user knows which roles
        are being requested before authorizing.
        """

        req_token = self.oauth_api.get_request_token(request_key)

        # fix expires
        # verify expiry first
        #now = datetime.datetime.utcnow()
        #expires_at = req_token['expires_at']
        #expires = datetime.datetime.strptime(expires_at, TIME_FORMAT)
        #if now > expires:
            #raise exception.Unauthorized(_('Request token is expired'))

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
        if not found:
            msg = _("User is not a member of the requested project")
            raise exception.ProjectNotFound(req_project_id)

        # finally authorize the token
        authed_token = self.oauth_api.authorize_request_token(
            request_key, user_id)

        to_return = {'token': {'oauth_verifier': authed_token['verifier']}}
        return to_return

    def _rebuild_url_from_environ(self, environ):
        url = environ['wsgi.url_scheme'] + '://'
        url += environ['HTTP_HOST']

        if not environ.get('PATH_INFO'):
            url += urllib.quote(environ.get('RAW_PATH_INFO', ''))
        else:
            url += urllib.quote(environ.get('PATH_INFO', ''))
        return url


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
        """List user authorizations.

        :param user_id: search for access tokens authorized by given user id
        :type user_id: string
        returns: list of access tokens the user has authorized

        """
        raise exception.NotImplemented()

    def delete_access_token(self, user_id, access_token_id):
        """Delete user authorization.

        :param user_id: authorizing user id
        :type user_id: string
        :param access_token_id: access token to delete
        :type access_token_id: string
        returns: None

        """
        raise exception.NotImplemented()

    def create_request_token(self, consumer_key, requested_roles,
                             requested_project, request_token_expiry):
        """Create request token.

        :param consumer_key: the key of the consumer
        :type consumer_key: string
        :param requested_roles: requested roles - comma separated
        :type requested_roles: string
        returns: request_token_ref

        """
        raise exception.NotImplemented()

    def get_request_token(self, request_token_key, requet_token_expiry):
        """Get request token.

        :param request_token_key: the key of the request token
        :type request_token_key: string
        :param requet_token_expiry: number of hours the token will last
        :type requet_token_expiry: int
        returns: request_token_ref

        """
        raise exception.NotImplemented()

    def get_access_token(self, access_token_key):
        """Get access token.

        :param access_token_key: the key of the access token
        :type access_token_key: string
        returns: access_token_ref

        """
        raise exception.NotImplemented()

    def authorize_request_token(self, request_key, user_id):
        """Authorize request token.

        :param request_key: the key of the request token, to be authorized
        :type request_key: string
        :param user_id: the id of the authorizing user
        :type user_id: string
        :param project_id: the project of the authorizing user
        :type project_id: string
        returns: verifier

        """
        raise exception.NotImplemented()

    def create_access_token(self, request_key, access_token_expiry):
        """Create access token.

        :param request_key: the key of the request token, to be deleted
        :type request_key: string
        :param access_token_expiry: number of days the access token will last
        :type access_token_expiry: int
        returns: access_token_ref

        """
        raise exception.NotImplemented()
