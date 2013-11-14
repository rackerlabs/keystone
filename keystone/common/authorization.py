# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 - 2012 Justin Santa Barbara
# All Rights Reserved.
#
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

import collections
import functools

from keystone.common import wsgi
from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging

# Environment variable used to convey the Keystone auth context
AUTH_CONTEXT_ENV = 'KEYSTONE_AUTH_CONTEXT'

LOG = logging.getLogger(__name__)
CONF = config.CONF


def build_policy_check_credentials(self, context):
    try:
        token_ref = self.token_api.get_token(context.get('token_id'))
    except exception.TokenNotFound:
        LOG.warning(_('RBAC: Invalid token'))
        raise exception.Unauthorized()

    # NOTE(jamielennox): whilst this maybe shouldn't be within this function
    # it would otherwise need to reload the token_ref from backing store.
    wsgi.validate_token_bind(context, token_ref)

    creds = {}
    if 'token_data' in token_ref and 'token' in token_ref['token_data']:
        #V3 Tokens
        token_data = token_ref['token_data']['token']
        try:
            creds['user_id'] = token_data['user']['id']
        except AttributeError:
            LOG.warning(_('RBAC: Invalid user'))
            raise exception.Unauthorized()

        if 'project' in token_data:
            creds['project_id'] = token_data['project']['id']
        else:
            LOG.debug(_('RBAC: Proceeding without project'))

        if 'domain' in token_data:
            creds['domain_id'] = token_data['domain']['id']

        if 'roles' in token_data:
            creds['roles'] = []
            for role in token_data['roles']:
                creds['roles'].append(role['name'])
    else:
        #v2 Tokens
        creds = token_ref.get('metadata', {}).copy()
        try:
            creds['user_id'] = token_ref['user'].get('id')
        except AttributeError:
            LOG.warning(_('RBAC: Invalid user'))
            raise exception.Unauthorized()
        try:
            creds['project_id'] = token_ref['tenant'].get('id')
        except AttributeError:
            LOG.debug(_('RBAC: Proceeding without tenant'))
        # NOTE(vish): this is pretty inefficient
        creds['roles'] = [self.assignment_api.get_role(role)['name']
                          for role in creds.get('roles', [])]

    return creds


def get_policy_check_credentials(self, action, context, kwargs):
    LOG.debug(_('RBAC: Authorizing %(action)s(%(kwargs)s)') % {
        'action': action,
        'kwargs': ', '.join(['%s=%s' % (k, kwargs[k]) for k in kwargs])})

    if ('environment' in context and
            AUTH_CONTEXT_ENV in context['environment']):
        return context['environment'].get(AUTH_CONTEXT_ENV)
    else:
        # NOTE(gyee): if auth context in not found, that means we are in a
        # rolling upgrade situation where new code is being used in conjunction
        # with old config and the new AuthContextMiddleware has not been
        # deployed yet. In the case, we still need to build the auth context
        # from the incoming auth token.
        return build_policy_check_credentials(self, context)


def flatten(d, parent_key=''):
    """Flatten a nested dictionary

    Converts a dictionary with nested values to a single level flat
    dictionary, with dotted notation for each key.

    """
    items = []
    for k, v in d.items():
        new_key = parent_key + '.' + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)


def protected(callback=None):
    """Wraps API calls with role based access controls (RBAC).

    This handles both the protection of the API parameters as well as any
    target entities for single-entity API calls.

    More complex API calls (for example that deal with several different
    entities) should pass in a callback function, that will be subsequently
    called to check protection for these multiple entities. This callback
    function should gather the appropriate entities needed and then call
    check_proetction() in the V3Controller class.

    """
    def wrapper(f):
        @functools.wraps(f)
        def inner(self, context, *args, **kwargs):
            if 'is_admin' in context and context['is_admin']:
                LOG.warning(_('RBAC: Bypassing authorization'))
            elif callback is not None:
                prep_info = {'f_name': f.__name__,
                             'input_attr': kwargs}
                callback(self, context, prep_info, *args, **kwargs)
            else:
                action = 'identity:%s' % f.__name__
                creds = get_policy_check_credentials(self, action,
                                                     context, kwargs)

                policy_dict = {}

                # Check to see if we need to include the target entity in our
                # policy checks.  We deduce this by seeing if the class has
                # specified a get_member() method and that kwargs contains the
                # appropriate entity id.
                if (hasattr(self, 'get_member_from_driver') and
                        self.get_member_from_driver is not None):
                    key = '%s_id' % self.member_name
                    if key in kwargs:
                        ref = self.get_member_from_driver(kwargs[key])
                        policy_dict['target'] = {self.member_name: ref}

                # TODO(henry-nash): Move this entire code to a member
                # method inside v3 Auth
                if context.get('subject_token_id') is not None:
                    token_ref = self.token_api.get_token(
                        context['subject_token_id'])
                    policy_dict.setdefault('target', {})
                    policy_dict['target'].setdefault(self.member_name, {})
                    policy_dict['target'][self.member_name]['user_id'] = (
                        token_ref['user_id'])
                    if 'domain' in token_ref['user']:
                        policy_dict['target'][self.member_name].setdefault(
                            'user', {})
                        policy_dict['target'][self.member_name][
                            'user'].setdefault('domain', {})
                        policy_dict['target'][self.member_name]['user'][
                            'domain']['id'] = (
                                token_ref['user']['domain']['id'])

                # Add in the kwargs, which means that any entity provided as a
                # parameter for calls like create and update will be included.
                policy_dict.update(kwargs)
                self.policy_api.enforce(creds, action, flatten(policy_dict))
                LOG.debug(_('RBAC: Authorization granted'))
            return f(self, context, *args, **kwargs)
        return inner
    return wrapper


def filterprotected(*filters):
    """Wraps filtered API calls with role based access controls (RBAC)."""

    def _filterprotected(f):
        @functools.wraps(f)
        def wrapper(self, context, **kwargs):
            if not context['is_admin']:
                action = 'identity:%s' % f.__name__
                creds = get_policy_check_credentials(self, action,
                                                     context, kwargs)
                # Now, build the target dict for policy check.  We include:
                #
                # - Any query filter parameters
                # - Data from the main url (which will be in the kwargs
                #   parameter) and would typically include the prime key
                #   of a get/update/delete call
                #
                # First  any query filter parameters
                target = dict()
                if len(filters) > 0:
                    for item in filters:
                        if item in context['query_string']:
                            target[item] = context['query_string'][item]

                    LOG.debug(_('RBAC: Adding query filter params (%s)'), (
                        ', '.join(['%s=%s' % (item, target[item])
                                  for item in target])))

                # Now any formal url parameters
                for key in kwargs:
                    target[key] = kwargs[key]

                self.policy_api.enforce(creds, action, flatten(target))

                LOG.debug(_('RBAC: Authorization granted'))
            else:
                LOG.warning(_('RBAC: Bypassing authorization'))
            return f(self, context, filters, **kwargs)
        return wrapper
    return _filterprotected
