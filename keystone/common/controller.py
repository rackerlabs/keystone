# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

import uuid

from keystone.common import authorization
from keystone.common import dependency
from keystone.common import wsgi
from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging
from keystone.openstack.common import versionutils


LOG = logging.getLogger(__name__)
CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id

v2_deprecated = versionutils.deprecated(what='v2 API',
                                        as_of=versionutils.deprecated.ICEHOUSE,
                                        in_favor_of='v3 API')


@dependency.requires('assignment_api', 'identity_api', 'policy_api',
                     'token_api', 'trust_api')
class V2Controller(wsgi.Application):
    """Base controller class for Identity API v2."""

    def _delete_tokens_for_trust(self, user_id, trust_id):
        self.token_api.delete_tokens(user_id, trust_id=trust_id)

    def _delete_tokens_for_user(self, user_id, project_id=None):
        #First delete tokens that could get other tokens.
        self.token_api.delete_tokens(user_id, tenant_id=project_id)

        #delete tokens generated from trusts
        for trust in self.trust_api.list_trusts_for_trustee(user_id):
            self._delete_tokens_for_trust(user_id, trust['id'])
        for trust in self.trust_api.list_trusts_for_trustor(user_id):
            self._delete_tokens_for_trust(trust['trustee_user_id'],
                                          trust['id'])

    def _delete_tokens_for_project(self, project_id):
        user_ids = self.assignment_api.list_user_ids_for_project(project_id)
        for user_id in user_ids:
            self._delete_tokens_for_user(user_id, project_id=project_id)

    def _delete_tokens_for_role(self, role_id):
        assignments = self.assignment_api.list_role_assignments_for_role(
            role_id=role_id)

        # Iterate over the assignments for this role and build the list of
        # user or user+project IDs for the tokens we need to delete
        user_ids = set()
        user_and_project_ids = list()
        for assignment in assignments:
            # If we have a project assignment, then record both the user and
            # project IDs so we can target the right token to delete. If it is
            # a domain assignment, we might as well kill all the tokens for
            # the user, since in the vast majority of cases all the tokens
            # for a user will be within one domain anyway, so not worth
            # trying to delete tokens for each project in the domain.
            if 'user_id' in assignment:
                if 'project_id' in assignment:
                    user_and_project_ids.append(
                        (assignment['user_id'], assignment['project_id']))
                elif 'domain_id' in assignment:
                    user_ids.add(assignment['user_id'])
            elif 'group_id' in assignment:
                # Add in any users for this group, being tolerant of any
                # cross-driver database integrity errors.
                try:
                    users = self.identity_api.list_users_in_group(
                        assignment['group_id'])
                except exception.GroupNotFound:
                    # Ignore it, but log a debug message
                    if 'project_id' in assignment:
                        target = _('Project (%s)') % assignment['project_id']
                    elif 'domain_id' in assignment:
                        target = _('Domain (%s)') % assignment['domain_id']
                    else:
                        target = _('Unknown Target')
                    msg = _('Group (%(group)s), referenced in assignment '
                            'for %(target)s, not found - ignoring.')
                    LOG.debug(msg, {'group': assignment['group_id'],
                                    'target': target})
                    continue

                if 'project_id' in assignment:
                    for user in users:
                        user_and_project_ids.append(
                            (user['id'], assignment['project_id']))
                elif 'domain_id' in assignment:
                    for user in users:
                        user_ids.add(user['id'])

        # Now process the built up lists.  Before issuing calls to delete any
        # tokens, let's try and minimize the number of calls by pruning out
        # any user+project deletions where a general token deletion for that
        # same user is also planned.
        user_and_project_ids_to_action = []
        for user_and_project_id in user_and_project_ids:
            if user_and_project_id[0] not in user_ids:
                user_and_project_ids_to_action.append(user_and_project_id)

        for user_id in user_ids:
            self._delete_tokens_for_user(user_id)
        for user_id, project_id in user_and_project_ids_to_action:
            self._delete_tokens_for_user(user_id, project_id)

    def _require_attribute(self, ref, attr):
        """Ensures the reference contains the specified attribute."""
        if ref.get(attr) is None or ref.get(attr) == '':
            msg = '%s field is required and cannot be empty' % attr
            raise exception.ValidationError(message=msg)

    def _normalize_domain_id(self, context, ref):
        """Fill in domain_id since v2 calls are not domain-aware.

        This will overwrite any domain_id that was inadvertently
        specified in the v2 call.

        """
        ref['domain_id'] = DEFAULT_DOMAIN_ID
        return ref

    @staticmethod
    def filter_domain_id(ref):
        """Remove domain_id since v2 calls are not domain-aware."""
        ref.pop('domain_id', None)
        return ref


@dependency.requires('identity_api', 'policy_api', 'token_api')
class V3Controller(V2Controller):
    """Base controller class for Identity API v3.

    Child classes should set the ``collection_name`` and ``member_name`` class
    attributes, representing the collection of entities they are exposing to
    the API. This is required for supporting self-referential links,
    pagination, etc.

    """

    collection_name = 'entities'
    member_name = 'entity'
    get_member_from_driver = None

    def _delete_tokens_for_group(self, group_id):
        user_refs = self.identity_api.list_users_in_group(group_id)
        for user in user_refs:
            self._delete_tokens_for_user(user['id'])

    @classmethod
    def base_url(cls, path=None):
        endpoint = CONF.public_endpoint % CONF

        # allow a missing trailing slash in the config
        if endpoint[-1] != '/':
            endpoint += '/'

        url = endpoint + 'v3'

        if path:
            return url + path
        else:
            return url + '/' + cls.collection_name

    @classmethod
    def _add_self_referential_link(cls, ref):
        ref.setdefault('links', {})
        ref['links']['self'] = cls.base_url() + '/' + ref['id']

    @classmethod
    def wrap_member(cls, context, ref):
        cls._add_self_referential_link(ref)
        return {cls.member_name: ref}

    @classmethod
    def wrap_collection(cls, context, refs, filters=[]):
        for f in filters:
            refs = cls.filter_by_attribute(context, refs, f)

        refs = cls.paginate(context, refs)

        for ref in refs:
            cls.wrap_member(context, ref)

        container = {cls.collection_name: refs}
        container['links'] = {
            'next': None,
            'self': cls.base_url(path=context['path']),
            'previous': None}
        return container

    @classmethod
    def paginate(cls, context, refs):
        """Paginates a list of references by page & per_page query strings."""
        # FIXME(dolph): client needs to support pagination first
        return refs

        page = context['query_string'].get('page', 1)
        per_page = context['query_string'].get('per_page', 30)
        return refs[per_page * (page - 1):per_page * page]

    @classmethod
    def filter_by_attribute(cls, context, refs, attr):
        """Filters a list of references by query string value."""

        def _attr_match(ref_attr, val_attr):
            """Matches attributes allowing for booleans as strings.

            We test explicitly for a value that defines it as 'False',
            which also means that the existence of the attribute with
            no value implies 'True'

            """
            if type(ref_attr) is bool:
                if (isinstance(val_attr, basestring) and
                        val_attr == '0'):
                    val = False
                else:
                    val = True
                return (ref_attr == val)
            else:
                return (ref_attr == val_attr)

        if attr in context['query_string']:
            value = context['query_string'][attr]
            return [r for r in refs if _attr_match(
                authorization.flatten(r).get(attr), value)]
        return refs

    def _require_matching_id(self, value, ref):
        """Ensures the value matches the reference's ID, if any."""
        if 'id' in ref and ref['id'] != value:
            raise exception.ValidationError('Cannot change ID')

    def _assign_unique_id(self, ref):
        """Generates and assigns a unique identifer to a reference."""
        ref = ref.copy()
        ref['id'] = uuid.uuid4().hex
        return ref

    def _get_domain_id_for_request(self, context):
        """Get the domain_id for a v3 call."""

        if context['is_admin']:
            return DEFAULT_DOMAIN_ID

        # Fish the domain_id out of the token
        #
        # We could make this more efficient by loading the domain_id
        # into the context in the wrapper function above (since
        # this version of normalize_domain will only be called inside
        # a v3 protected call).  However, this optimization is probably not
        # worth the duplication of state
        try:
            token_ref = self.token_api.get_token(context['token_id'])
        except exception.TokenNotFound:
            LOG.warning(_('Invalid token in _get_domain_id_for_request'))
            raise exception.Unauthorized()

        if 'domain' in token_ref:
            return token_ref['domain']['id']
        else:
            return DEFAULT_DOMAIN_ID

    def _normalize_domain_id(self, context, ref):
        """Fill in domain_id if not specified in a v3 call."""
        if 'domain_id' not in ref:
            ref['domain_id'] = self._get_domain_id_for_request(context)
        return ref

    @staticmethod
    def filter_domain_id(ref):
        """Override v2 filter to let domain_id out for v3 calls."""
        return ref

    def check_protection(self, context, prep_info, target_attr=None):
        """Provide call protection for complex target attributes.

        As well as including the standard parameters from the original API
        call (which is passed in prep_info), this call will add in any
        additional entities or attributes (passed in target_attr), so that
        they can be referenced by policy rules.

         """
        if 'is_admin' in context and context['is_admin']:
            LOG.warning(_('RBAC: Bypassing authorization'))
        else:
            action = 'identity:%s' % prep_info['f_name']
            # TODO(henry-nash) need to log the target attributes as well
            creds = authorization.get_policy_check_credentials(
                self.assignment_api,
                self.token_api,
                action,
                context,
                prep_info['input_attr'])
            # Build the dict the policy engine will check against from both the
            # parameters passed into the call we are protecting (which was
            # stored in the prep_info by protected()), plus the target
            # attributes provided.
            policy_dict = {}
            if target_attr:
                policy_dict = {'target': target_attr}
            policy_dict.update(prep_info['input_attr'])
            self.policy_api.enforce(
                creds, action, authorization.flatten(policy_dict))
            LOG.debug(_('RBAC: Authorization granted'))
