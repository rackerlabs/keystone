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
from keystone import token

CONF = config.CONF
LOG = logging.getLogger(__name__)

EXTENSION_DATA = {
    'name': 'OpenStack OAUTH10A API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-OAUTH10A/v1.0',
    'alias': 'OS-OAUTH10A',
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


@dependency.provider('oauth_api')
class Manager(manager.Manager):
    """Default pivot point for the delegated auth credentials backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.oauth.driver)


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

    def list_user_authorizations(self, user_id):
        """List user authorizations.

        :param user_id: search for access tokens authorized by given user id
        :type user_id: string
        returns: list of access tokens the user has authorized

        """
        raise exception.NotImplemented()

    def delete_user_authorization(self, user_id, authz_id):
        """Delete user authorization.

        :param user_id: authorizing user id
        :type user_id: string
        :param authz_id: access token id to delete
        :type authz_id: string
        returns: None

        """
        raise exception.NotImplemented()

    def create_request_token(self, consumer_key, requested_roles):
        """Create request token.

        :param consumer_key: the key of the consumer
        :type consumer_key: string
        :param requested_roles: requested roles - comma separated
        :type requested_roles: string
        returns: request_token_ref

        """
        raise exception.NotImplemented()

    def get_request_token(self, request_token_key):
        """Get request token.

        :param request_token_key: the key of the request token
        :type request_token_key: string
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

    def authorize_request_token(self, request_key, user_id, project_id):
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

    def create_access_token(self, request_key):
        """Create access token.

        :param request_key: the key of the request token, to be deleted
        :type request_key: string
        returns: access_token_ref

        """
        raise exception.NotImplemented()


class DelegatedAuthExtension(wsgi.ExtensionRouter):
    """API Endpoints for the Delegated Auth extension.

    The goal of this extension is to allow third-party service providers
    to acquire tokens with a limited subset of a user's roles for acting
    on behalf of that user. This is done using an oauth-similar flow and
    api.

    The API looks like:

      # Basic admin-only consumer crud
      POST /OS-OAUTH10A/consumers
      GET /OS-OAUTH10A/consumers
      PUT /OS-OAUTH10A/consumers/$consumer_id
      GET /OS-OAUTH10A/consumers/$consumer_id
      DELETE /OS-OAUTH10A/consumers/$consumer_id

      # User access token crud
      GET /OS-OAUTH10A/user/$user_id/authorizations
      DELETE /OS-OAUTH10A/user/$user_id/authorization/$access_token

      # Public interface for third-party
      GET /OS-OAUTH10A/authenticate  # request a keystone token using an
                                         # access token

      # Public oauth interface for third-party
      GET /OS-OAUTH10A/request_token  # get a request token for user to authz
      GET /OS-OAUTH10A/access_token  # get an access token when a request
                               #  token has has been authorized

      # Public oauth interface for user
      GET /OS-OAUTH10A/authorization_pin  # a url the user may request to get
                                    # an authz PIN to hand to the service
      POST /OS-OAUTH10A/authorize  # authorize a request token

    """

    def add_routes(self, mapper):
        consumer_controller = ConsumerCrudV3()
        authz_controller = AuthorizationCrudV3()
        oauth_controller = OauthFlowManiaV3()

        # basic admin-only consumer crud
        mapper.connect(
            '/OS-OAUTH10A/consumers',
            controller=consumer_controller,
            action='create_consumer',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/OS-OAUTH10A/consumers/{consumer_id}',
            controller=consumer_controller,
            action='get_consumer',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-OAUTH10A/consumers/{consumer_id}',
            controller=consumer_controller,
            action='update_consumer',
            conditions=dict(method=['PATCH']))
        mapper.connect(
            '/OS-OAUTH10A/consumers/{consumer_id}',
            controller=consumer_controller,
            action='delete_consumer',
            conditions=dict(method=['DELETE']))
        mapper.connect(
            '/OS-OAUTH10A/consumers',
            controller=consumer_controller,
            action='list_consumers',
            conditions=dict(method=['GET']))

        # user accesss token crud
        mapper.connect(
            '/OS-OAUTH10A/user/{user_id}/authorizations',
            controller=authz_controller,
            action='list_user_authorizations',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-OAUTH10A/user/{user_id}/authorization/{authz_id}',
            controller=authz_controller,
            action='delete_user_authorization',
            conditions=dict(method=['DELETE']))

        # request keystone token
        mapper.connect(
            '/OS-OAUTH10A/authenticate',
            controller=oauth_controller,
            action='authenticate',
            conditions=dict(method=['GET']))

        # public oauth third-party
        mapper.connect(
            '/OS-OAUTH10A/request_token',
            controller=oauth_controller,
            action='create_request_token',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-OAUTH10A/access_token',
            controller=oauth_controller,
            action='create_access_token',
            conditions=dict(method=['GET']))

        #public oauth user
        mapper.connect(
            '/OS-OAUTH10A/authorization_pin',
            controller=oauth_controller,
            action='get_authorization_pin',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/OS-OAUTH10A/authorize/{request_id}/{requested_roles}',
            controller=oauth_controller,
            action='authorize',
            conditions=dict(method=['POST']))


@dependency.requires('oauth_api', 'token_api')
class ConsumerCrudV3(controller.V3Controller):
    collection_name = 'consumers'
    member_name = 'consumer'

    def create_consumer(self, context, consumer):
        ref = self._assign_unique_id(self._normalize_dict(consumer))
        ref = self._normalize_domain_id(context, ref)
        consumer_ref = self.oauth_api.create_consumer(ref)
        return ConsumerCrudV3.wrap_member(context, consumer_ref)

    def update_consumer(self, context, consumer_id, consumer):
        self._require_matching_id(consumer_id, consumer)
        ref = self._normalize_dict(consumer)
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
        # when deleting a consumer, we must delete generated keystone tokens
        self._delete_tokens_for_user(user_id)
        # deleting the request/access tokens is taken care of in the backend
        self.oauth_api.delete_consumer(consumer_id)


@dependency.requires('oauth_api')
class AuthorizationCrudV3(controller.V3Controller):
    collection_name = 'authorizations'
    member_name = 'authorization'

    def list_user_authorizations(self, context, user_id):
        refs = self.oauth_api.list_user_authorizations(user_id)
        return AuthorizationCrudV3.wrap_collection(context, refs)

    def delete_user_authorization(self, context, user_id, authz_id):
        self._delete_tokens_for_user(user_id)
        return self.oauth_api.delete_user_authorization(
            user_id, authz_id)


@dependency.requires('oauth_api', 'token_api', 'assignment_api',
                     'identity_api', 'token_provider_api')
class OauthFlowManiaV3(controller.V3Controller):
    collection_name = 'not_used'
    member_name = 'not_used'

    def create_request_token(self, context):
        request = context['request']
        consumer_key = request.GET.get('oauth_consumer_key')
        requested_roles = request.GET.get('requested_roles')
        if not consumer_key:
            raise exception.ValidationError(
                attribute='oauth_consumer_key', target='request')
        if not requested_roles:
            raise exception.ValidationError(
                attribute='requested_roles', target='request')

        role_list = requested_roles.split(',')
        consumer_ref = self.oauth_api.get_consumer(consumer_key)
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

        roles_params = params['requested_roles']
        roles_params_list = roles_params.split(',')
        if roles_params_list != role_list:
            msg = 'Non-oauth parameters do not match'
            raise exception.Unauthorized(message=msg)

        all_roles = self.identity_api.list_roles()
        all_roles_list = list()
        for role in all_roles:
            all_roles_list.append(role['name'])

        if set(role_list).issubset(set(all_roles_list)):
            token_ref = self.oauth_api.create_request_token(consumer_key,
                                                            requested_roles)
        else:
            msg = 'role provided does not exist, try using role name only'
            raise exception.Unauthorized(message=msg)

        to_return = {'token':
                     {'request_token_key': token_ref['request_key'],
                      'request_token_secret': token_ref['request_secret']
                      }
                     }
        return to_return

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

        consumer = self.oauth_api.get_consumer(consumer_key)
        req_token = self.oauth_api.get_request_token(
            request_token_key)

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
            msg = 'There should not be any non-oauth parameters'
            raise exception.Unauthorized(message=msg)

        if req_token['consumer_key'] != consumer_key:
            msg = 'provided consumer key does not match stored consumer key'
            raise exception.Unauthorized(message=msg)

        if req_token['verifier'] != oauth_verifier:
            msg = 'provided verifier does not match stored verifier'
            raise exception.Unauthorized(message=msg)

        if req_token['request_key'] != request_token_key:
            msg = 'provided request key does not match stored request key'
            raise exception.Unauthorized(message=msg)

        if (not req_token.get('user_id') or not req_token.get('project_id')):
            msg = 'request token does not have a user id or project id'
            raise exception.Unauthorized(message=msg)

        token_ref = self.oauth_api.create_access_token(request_token_key)

        to_return = {'token':
                     {'access_token_key': token_ref['access_key'],
                      'access_token_secret': token_ref['access_secret']
                      }
                     }
        return to_return

    def authenticate(self, context):
        """Turn a signed request with an access key into a keystone token."""
        request = context['request']
        consumer_key = request.GET.get('oauth_consumer_key')
        access_id = request.GET.get('oauth_token')

        if not consumer_key:
            raise exception.ValidationError(
                attribute='oauth_consumer_key', target='request')
        if not access_id:
            raise exception.ValidationError(
                attribute='oauth_token', target='request')

        consumer = self.oauth_api.get_consumer(consumer_key)
        acc_token = self.oauth_api.get_access_token(access_id)

        consumer_obj = oauth.Consumer(key=consumer['consumer_key'],
                                      secret=consumer['consumer_secret'])
        acc_token_obj = oauth.Token(key=acc_token['access_key'],
                                    secret=acc_token['access_secret'])

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
                                             token=acc_token_obj)

        if len(params) != 0:
            msg = 'There should not be any non-oauth parameters'
            raise exception.Unauthorized(message=msg)

        if acc_token['consumer_key'] != consumer_key:
            msg = 'provided consumer key does not match stored consumer key'
            raise exception.Unauthorized(message=msg)

        user_id = acc_token['user_id']
        project_id = acc_token['project_id']

        return self._create_keystone_token(user_id, project_id)

    def authorize(self, context, request_id, requested_roles):
        """An authenticated user is going to authorize a request token.

        As a security precaution, the requested roles must match those in
        the request token. Because this is in a CLI-only world at the moment,
        there is not another easy way to make sure the user knows which roles
        are being requested before authorizing.
        """
        req_token = self.oauth_api.get_request_token(request_id)
        req_token_roles = req_token['requested_roles']
        req_token_roles_list = req_token_roles.split(',')

        creds = self._create_user_creds(context['token_id'])
        # verify that the user has the requested roles
        # and verify that the role was requested in the req token
        requested_roles_list = requested_roles.split(',')
        roles_as_set = set(req_token_roles_list)
        for role in requested_roles_list:
            if (role not in creds['roles'] and
                    role not in roles_as_set):
                msg = 'authorizing user does not have role required'
                raise exception.Unauthorized(message=msg)

        authed_token = self.oauth_api.authorize_request_token(
            request_id, creds['user_id'], creds['project_id'])

        to_return = {'token': {'oauth_verifier': authed_token['verifier']}}
        return to_return

    def get_authorization_pin(self, context):
        request = context['request']
        request_id = request.GET.get('oauth_token')
        req_token = self.oauth_api.get_request_token(request_id)
        verifier_pin = req_token['verifier']
        return {'token': {'oauth_verifier': verifier_pin}}

    def _create_user_creds(self, user_token):
        user_token_ref = self.token_api.get_token(token_id=user_token)
        creds = user_token_ref['metadata'].copy()
        creds['roles'] = [self.identity_api.get_role(role)['name']
                          for role in creds.get('roles', [])]
        creds['user_id'] = user_token_ref['user'].get('id')
        creds['project_id'] = user_token_ref['tenant'].get('id')
        return creds

    def _rebuild_url_from_environ(self, environ):
        url = environ['wsgi.url_scheme'] + '://'
        url += environ['HTTP_HOST']

        if environ['wsgi.url_scheme'] == 'https':
            url += urllib.quote(environ.get('PATH_INFO', ''))
        else:
            url += urllib.quote(environ.get('RAW_PATH_INFO', ''))
        return url

    def _create_keystone_token(self, user_id, project_id):
        tenant_ref = self.identity_api.get_project(project_id)
        user_ref = self.identity_api.get_user(user_id)
        domain_id = user_ref['domain_id']

        metadata_ref = {}
        metadata_ref['roles'] = (
            self.identity_api.get_roles_for_user_and_project(
                user_ref['id'], tenant_ref['id']))

        # Validate that the auth info is valid and nothing is disabled
        token.validate_auth_info(self, user_ref, tenant_ref)

        (token_id, token_data) = self.token_provider_api.issue_token(
            version=token.provider.V3,
            project_id=project_id,
            user_id=user_id,
            domain_id=domain_id,
            trust=None,
            method_names=list(),
            auth_context=None,
            metadata_ref=metadata_ref,
            include_catalog=False)

        token_data['token']['id'] = token_id
        return token_data
