# Copyright 2013 OpenStack Foundation
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

from keystone.common import wsgi
from keystone.contrib import oauth1
from keystone.contrib.oauth1 import controllers


class OAuth1Extension(wsgi.V3ExtensionRouter):
    """API Endpoints for the OAuth1 extension.

    The goal of this extension is to allow third-party service providers
    to acquire tokens with a limited subset of a user's roles for acting
    on behalf of that user. This is done using an oauth-similar flow and
    api.

    The API looks like::

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
      POST /OS-OAUTH1/request_token  # create a request token
      PUT /OS-OAUTH1/authorize  # authorize a request token
      POST /OS-OAUTH1/access_token  # create an access token

    """

    def add_routes(self, mapper):
        # This is needed for dependency injection,
        # it loads the OAuth driver which registers it as a dependency.
        oauth1.Manager()
        consumer_controller = controllers.ConsumerCrudV3()
        access_token_controller = controllers.AccessTokenCrudV3()
        access_token_roles_controller = controllers.AccessTokenRolesV3()
        oauth_controller = controllers.OAuthControllerV3()

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
            conditions=dict(method=['POST']))
        mapper.connect(
            '/OS-OAUTH1/access_token',
            controller=oauth_controller,
            action='create_access_token',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/OS-OAUTH1/authorize/{request_token_id}',
            controller=oauth_controller,
            action='authorize_request_token',
            conditions=dict(method=['PUT']))

    def _get_version_data(self):
        return (
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'consumers',
             {
                 'href': '/OS-OAUTH1/consumers',
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'consumer',
             {
                 'href-template': '/OS-OAUTH1/consumers/{consumer_id}',
                 'href-vars': {
                     'consumer_id': 'http://docs.openstack.org/identity/rel/'
                     'v3/ext/OS-OAUTH1/1.0/param/consumer_id'
                 },
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'user_access_tokens',
             {
                 'href-template': '/users/{user_id}/OS-OAUTH1/access_tokens',
                 'href-vars': {
                     'user_id':
                     'http://docs.openstack.org/identity/v3/param/user_id',
                 },
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'user_access_token',
             {
                 'href-template': '/users/{user_id}/OS-OAUTH1/access_tokens/'
                 '{access_token_id}',
                 'href-vars': {
                     'access_token_id':
                     'http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/'
                     '1.0/param/access_token_id',
                     'user_id':
                     'http://docs.openstack.org/identity/v3/param/user_id',
                 },
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'user_access_token_roles',
             {
                 'href-template': '/users/{user_id}/OS-OAUTH1/access_tokens/'
                 '{access_token_id}/roles',
                 'href-vars': {
                     'access_token_id':
                     'http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/'
                     '1.0/param/access_token_id',
                     'user_id':
                     'http://docs.openstack.org/identity/v3/param/user_id',
                 },
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'user_access_token_role',
             {
                 'href-template': '/users/{user_id}/OS-OAUTH1/access_tokens/'
                 '{access_token_id}/roles/{role_id}',
                 'href-vars': {
                     'access_token_id':
                     'http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/'
                     '1.0/param/access_token_id',
                     'role_id':
                     'http://docs.openstack.org/identity/v3/param/role_id',
                     'user_id':
                     'http://docs.openstack.org/identity/v3/param/user_id',
                 },
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'request_tokens',
             {
                 'href': '/OS-OAUTH1/request_token',
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'access_tokens',
             {
                 'href': '/OS-OAUTH1/access_token',
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/1.0/'
             'authorize_request_token',
             {
                 'href-template': '/OS-OAUTH1/authorize/{request_token_id}',
                 'href-vars': {
                     'request_token_id':
                     'http://docs.openstack.org/identity/rel/v3/ext/OS-OAUTH1/'
                     '1.0/param/request_token_id',
                 },
             }
             ),
        )
