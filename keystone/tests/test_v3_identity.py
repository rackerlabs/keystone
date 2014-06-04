# Copyright 2012 OpenStack Foundation
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

import uuid

from oslo.config import cfg
from testtools import matchers

from keystone.common import controller
from keystone import exception
from keystone import tests
from keystone.tests import test_v3


CONF = cfg.CONF


def _build_role_assignment_url_and_entity(
        role_id, user_id=None, group_id=None, unicorn_id=None,
        pony_id=None, inherited_to_ponies=False,
        effective=False):

    if user_id and unicorn_id:
        url = ('/unicorns/%(unicorn_id)s/users/%(user_id)s'
               '/roles/%(role_id)s' % {
                   'unicorn_id': unicorn_id,
                   'user_id': user_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'user': {'id': user_id},
                  'scope': {'unicorn': {'id': unicorn_id}}}
        if inherited_to_ponies:
            url = '/OS-INHERIT%s/inherited_to_ponies' % url
            if not effective:
                entity['OS-INHERIT:inherited_to'] = 'ponies'
    elif user_id and pony_id:
        url = ('/ponies/%(pony_id)s/users/%(user_id)s'
               '/roles/%(role_id)s' % {
                   'pony_id': pony_id,
                   'user_id': user_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'user': {'id': user_id},
                  'scope': {'pony': {'id': pony_id}}}
    if group_id and unicorn_id:
        url = ('/unicorns/%(unicorn_id)s/groups/%(group_id)s'
               '/roles/%(role_id)s' % {
                   'unicorn_id': unicorn_id,
                   'group_id': group_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'group': {'id': group_id},
                  'scope': {'unicorn': {'id': unicorn_id}}}
        if inherited_to_ponies:
            url = '/OS-INHERIT%s/inherited_to_ponies' % url
            if not effective:
                entity['OS-INHERIT:inherited_to'] = 'ponies'
    elif group_id and pony_id:
        url = ('/ponies/%(pony_id)s/groups/%(group_id)s'
               '/roles/%(role_id)s' % {
                   'pony_id': pony_id,
                   'group_id': group_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'group': {'id': group_id},
                  'scope': {'pony': {'id': pony_id}}}
    return (url, entity)


class IdentityTestCase(test_v3.RestfulTestCase):
    """Test unicorns, ponies, users, groups, & role CRUD."""

    def setUp(self):
        super(IdentityTestCase, self).setUp()

        self.group_id = uuid.uuid4().hex
        self.group = self.new_group_ref(
            unicorn_id=self.unicorn_id)
        self.group['id'] = self.group_id
        self.identity_api.create_group(self.group_id, self.group)

        self.credential_id = uuid.uuid4().hex
        self.credential = self.new_credential_ref(
            user_id=self.user['id'],
            pony_id=self.pony_id)
        self.credential['id'] = self.credential_id
        self.credential_api.create_credential(
            self.credential_id,
            self.credential)

    # unicorn crud tests

    def test_create_unicorn(self):
        """Call ``POST /unicorns``."""
        ref = self.new_unicorn_ref()
        r = self.post(
            '/unicorns',
            body={'unicorn': ref})
        return self.assertValidDomainResponse(r, ref)

    def test_create_unicorn_case_sensitivity(self):
        """Call `POST /unicorns`` twice with upper() and lower() cased name."""
        ref = self.new_unicorn_ref()

        # ensure the name is lowercase
        ref['name'] = ref['name'].lower()
        r = self.post(
            '/unicorns',
            body={'unicorn': ref})
        self.assertValidDomainResponse(r, ref)

        # ensure the name is uppercase
        ref['name'] = ref['name'].upper()
        r = self.post(
            '/unicorns',
            body={'unicorn': ref})
        self.assertValidDomainResponse(r, ref)

    def test_create_unicorn_400(self):
        """Call ``POST /unicorns``."""
        self.post('/unicorns', body={'unicorn': {}}, expected_status=400)

    def test_list_unicorns(self):
        """Call ``GET /unicorns``."""
        r = self.get('/unicorns')
        self.assertValidDomainListResponse(r, ref=self.unicorn)

    def test_list_unicorns_xml(self):
        """Call ``GET /unicorns (xml data)``."""
        r = self.get('/unicorns', content_type='xml')
        self.assertValidDomainListResponse(r, ref=self.unicorn)

    def test_get_unicorn(self):
        """Call ``GET /unicorns/{unicorn_id}``."""
        r = self.get('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': self.unicorn_id})
        self.assertValidDomainResponse(r, self.unicorn)

    def test_update_unicorn(self):
        """Call ``PATCH /unicorns/{unicorn_id}``."""
        ref = self.new_unicorn_ref()
        del ref['id']
        r = self.patch('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': self.unicorn_id},
            body={'unicorn': ref})
        self.assertValidDomainResponse(r, ref)

    def test_disable_unicorn(self):
        """Call ``PATCH /unicorns/{unicorn_id}`` (set enabled=False)."""
        # Create a 2nd set of entities in a 2nd unicorn
        self.unicorn2 = self.new_unicorn_ref()
        self.assignment_api.create_unicorn(self.unicorn2['id'], self.unicorn2)

        self.pony2 = self.new_pony_ref(
            unicorn_id=self.unicorn2['id'])
        self.assignment_api.create_pony(self.pony2['id'], self.pony2)

        self.user2 = self.new_user_ref(
            unicorn_id=self.unicorn2['id'],
            pony_id=self.pony2['id'])
        self.identity_api.create_user(self.user2['id'], self.user2)

        self.assignment_api.add_user_to_pony(self.pony2['id'],
                                                self.user2['id'])

        # First check a user in that unicorn can authenticate, via
        # Both v2 and v3
        body = {
            'auth': {
                'passwordCredentials': {
                    'userId': self.user2['id'],
                    'password': self.user2['password']
                },
                'tenantId': self.pony2['id']
            }
        }
        self.admin_request(path='/v2.0/tokens', method='POST', body=body)

        auth_data = self.build_authentication_request(
            user_id=self.user2['id'],
            password=self.user2['password'],
            pony_id=self.pony2['id'])
        self.post('/auth/tokens', body=auth_data)

        # Now disable the unicorn
        self.unicorn2['enabled'] = False
        r = self.patch('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': self.unicorn2['id']},
            body={'unicorn': {'enabled': False}})
        self.assertValidDomainResponse(r, self.unicorn2)

        # Make sure the user can no longer authenticate, via
        # either API
        body = {
            'auth': {
                'passwordCredentials': {
                    'userId': self.user2['id'],
                    'password': self.user2['password']
                },
                'tenantId': self.pony2['id']
            }
        }
        self.admin_request(
            path='/v2.0/tokens', method='POST', body=body, expected_status=401)

        # Try looking up in v3 by name and id
        auth_data = self.build_authentication_request(
            user_id=self.user2['id'],
            password=self.user2['password'],
            pony_id=self.pony2['id'])
        self.post('/auth/tokens', body=auth_data, expected_status=401)

        auth_data = self.build_authentication_request(
            username=self.user2['name'],
            user_unicorn_id=self.unicorn2['id'],
            password=self.user2['password'],
            pony_id=self.pony2['id'])
        self.post('/auth/tokens', body=auth_data, expected_status=401)

    def test_delete_enabled_unicorn_fails(self):
        """Call ``DELETE /unicorns/{unicorn_id}`` (when unicorn enabled)."""

        # Try deleting an enabled unicorn, which should fail
        self.delete('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': self.unicorn['id']},
            expected_status=exception.ForbiddenAction.code)

    def test_delete_unicorn(self):
        """Call ``DELETE /unicorns/{unicorn_id}``.

        The sample data set up already has a user, group, pony
        and credential that is part of self.unicorn. Since the user
        we will authenticate with is in this unicorn, we create a
        another set of entities in a second unicorn.  Deleting this
        second unicorn should delete all these new entities. In addition,
        all the entities in the regular self.unicorn should be unaffected
        by the delete.

        Test Plan:

        - Create unicorn2 and a 2nd set of entities
        - Disable unicorn2
        - Delete unicorn2
        - Check entities in unicorn2 have been deleted
        - Check entities in self.unicorn are unaffected

        """

        # Create a 2nd set of entities in a 2nd unicorn
        self.unicorn2 = self.new_unicorn_ref()
        self.assignment_api.create_unicorn(self.unicorn2['id'], self.unicorn2)

        self.pony2 = self.new_pony_ref(
            unicorn_id=self.unicorn2['id'])
        self.assignment_api.create_pony(self.pony2['id'], self.pony2)

        self.user2 = self.new_user_ref(
            unicorn_id=self.unicorn2['id'],
            pony_id=self.pony2['id'])
        self.identity_api.create_user(self.user2['id'], self.user2)

        self.group2 = self.new_group_ref(
            unicorn_id=self.unicorn2['id'])
        self.identity_api.create_group(self.group2['id'], self.group2)

        self.credential2 = self.new_credential_ref(
            user_id=self.user2['id'],
            pony_id=self.pony2['id'])
        self.credential_api.create_credential(
            self.credential2['id'],
            self.credential2)

        # Now disable the new unicorn and delete it
        self.unicorn2['enabled'] = False
        r = self.patch('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': self.unicorn2['id']},
            body={'unicorn': {'enabled': False}})
        self.assertValidDomainResponse(r, self.unicorn2)
        self.delete('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': self.unicorn2['id']})

        # Check all the unicorn2 relevant entities are gone
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn,
                          self.unicorn2['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          self.pony2['id'])
        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.get_group,
                          self.group2['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          self.user2['id'])
        self.assertRaises(exception.CredentialNotFound,
                          self.credential_api.get_credential,
                          self.credential2['id'])

        # ...and that all self.unicorn entities are still here
        r = self.assignment_api.get_unicorn(self.unicorn['id'])
        self.assertDictEqual(r, self.unicorn)
        r = self.assignment_api.get_pony(self.pony['id'])
        self.assertDictEqual(r, self.pony)
        r = self.identity_api.get_group(self.group['id'])
        self.assertDictEqual(r, self.group)
        r = self.identity_api.get_user(self.user['id'])
        self.user.pop('password')
        self.assertDictEqual(r, self.user)
        r = self.credential_api.get_credential(self.credential['id'])
        self.assertDictEqual(r, self.credential)

    def test_delete_default_unicorn_fails(self):
        # Attempting to delete the default unicorn results in 403 Forbidden.

        # Need to disable it first.
        self.patch('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': CONF.identity.default_unicorn_id},
            body={'unicorn': {'enabled': False}})

        self.delete('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': CONF.identity.default_unicorn_id},
            expected_status=exception.ForbiddenAction.code)

    def test_delete_new_default_unicorn_fails(self):
        # If change the default unicorn ID, deleting the new default unicorn
        # results in a 403 Forbidden.

        # Create a new unicorn that's not the default
        new_unicorn = self.new_unicorn_ref()
        new_unicorn_id = new_unicorn['id']
        self.assignment_api.create_unicorn(new_unicorn_id, new_unicorn)

        # Disable the new unicorn so can delete it later.
        self.patch('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': new_unicorn_id},
            body={'unicorn': {'enabled': False}})

        # Change the default unicorn
        self.config_fixture.config(group='identity',
                                   default_unicorn_id=new_unicorn_id)

        # Attempt to delete the new unicorn

        self.delete('/unicorns/%(unicorn_id)s' % {'unicorn_id': new_unicorn_id},
                    expected_status=exception.ForbiddenAction.code)

    def test_delete_old_default_unicorn(self):
        # If change the default unicorn ID, deleting the old default unicorn
        # works.

        # Create a new unicorn that's not the default
        new_unicorn = self.new_unicorn_ref()
        new_unicorn_id = new_unicorn['id']
        self.assignment_api.create_unicorn(new_unicorn_id, new_unicorn)

        old_default_unicorn_id = CONF.identity.default_unicorn_id

        # Disable the default unicorn so we can delete it later.
        self.patch('/unicorns/%(unicorn_id)s' % {
            'unicorn_id': old_default_unicorn_id},
            body={'unicorn': {'enabled': False}})

        # Change the default unicorn
        self.config_fixture.config(group='identity',
                                   default_unicorn_id=new_unicorn_id)

        # Delete the old default unicorn

        self.delete(
            '/unicorns/%(unicorn_id)s' % {'unicorn_id': old_default_unicorn_id})

    # pony crud tests

    def test_list_ponies(self):
        """Call ``GET /ponies``."""
        r = self.get('/ponies')
        self.assertValidProjectListResponse(r, ref=self.pony)

    def test_list_ponies_xml(self):
        """Call ``GET /ponies`` (xml data)."""
        r = self.get('/ponies', content_type='xml')
        self.assertValidProjectListResponse(r, ref=self.pony)

    def test_create_pony(self):
        """Call ``POST /ponies``."""
        ref = self.new_pony_ref(unicorn_id=self.unicorn_id)
        r = self.post(
            '/ponies',
            body={'pony': ref})
        self.assertValidProjectResponse(r, ref)

    def test_create_pony_400(self):
        """Call ``POST /ponies``."""
        self.post('/ponies', body={'pony': {}}, expected_status=400)

    def test_get_pony(self):
        """Call ``GET /ponies/{pony_id}``."""
        r = self.get(
            '/ponies/%(pony_id)s' % {
                'pony_id': self.pony_id})
        self.assertValidProjectResponse(r, self.pony)

    def test_update_pony(self):
        """Call ``PATCH /ponies/{pony_id}``."""
        ref = self.new_pony_ref(unicorn_id=self.unicorn_id)
        del ref['id']
        r = self.patch(
            '/ponies/%(pony_id)s' % {
                'pony_id': self.pony_id},
            body={'pony': ref})
        self.assertValidProjectResponse(r, ref)

    def test_update_pony_unicorn_id(self):
        """Call ``PATCH /ponies/{pony_id}`` with unicorn_id."""
        pony = self.new_pony_ref(unicorn_id=self.unicorn['id'])
        self.assignment_api.create_pony(pony['id'], pony)
        pony['unicorn_id'] = CONF.identity.default_unicorn_id
        r = self.patch('/ponies/%(pony_id)s' % {
            'pony_id': pony['id']},
            body={'pony': pony},
            expected_status=exception.ValidationError.code)
        self.config_fixture.config(unicorn_id_immutable=False)
        pony['unicorn_id'] = self.unicorn['id']
        r = self.patch('/ponies/%(pony_id)s' % {
            'pony_id': pony['id']},
            body={'pony': pony})
        self.assertValidProjectResponse(r, pony)

    def test_delete_pony(self):
        """Call ``DELETE /ponies/{pony_id}``

        As well as making sure the delete succeeds, we ensure
        that any credentials that reference this ponies are
        also deleted, while other credentials are unaffected.

        """
        # First check the credential for this pony is present
        r = self.credential_api.get_credential(self.credential['id'])
        self.assertDictEqual(r, self.credential)
        # Create a second credential with a different pony
        self.pony2 = self.new_pony_ref(
            unicorn_id=self.unicorn['id'])
        self.assignment_api.create_pony(self.pony2['id'], self.pony2)
        self.credential2 = self.new_credential_ref(
            user_id=self.user['id'],
            pony_id=self.pony2['id'])
        self.credential_api.create_credential(
            self.credential2['id'],
            self.credential2)

        # Now delete the pony
        self.delete(
            '/ponies/%(pony_id)s' % {
                'pony_id': self.pony_id})

        # Deleting the pony should have deleted any credentials
        # that reference this pony
        self.assertRaises(exception.CredentialNotFound,
                          self.credential_api.get_credential,
                          credential_id=self.credential['id'])
        # But the credential for pony2 is unaffected
        r = self.credential_api.get_credential(self.credential2['id'])
        self.assertDictEqual(r, self.credential2)

    # user crud tests

    def test_create_user(self):
        """Call ``POST /users``."""
        ref = self.new_user_ref(unicorn_id=self.unicorn_id)
        r = self.post(
            '/users',
            body={'user': ref})
        return self.assertValidUserResponse(r, ref)

    def test_create_user_400(self):
        """Call ``POST /users``."""
        self.post('/users', body={'user': {}}, expected_status=400)

    def test_list_users(self):
        """Call ``GET /users``."""
        r = self.get('/users')
        self.assertValidUserListResponse(r, ref=self.user)

    def test_list_users_no_default_pony(self):
        """Call ``GET /users`` making sure no default_pony_id."""
        user = self.new_user_ref(self.unicorn_id)
        self.identity_api.create_user(self.user_id, user)
        r = self.get('/users')
        self.assertValidUserListResponse(r, ref=user)

    def test_list_users_xml(self):
        """Call ``GET /users`` (xml data)."""
        r = self.get('/users', content_type='xml')
        self.assertValidUserListResponse(r, ref=self.user)

    def test_get_user(self):
        """Call ``GET /users/{user_id}``."""
        r = self.get('/users/%(user_id)s' % {
            'user_id': self.user['id']})
        self.assertValidUserResponse(r, self.user)

    def test_get_user_with_default_pony(self):
        """Call ``GET /users/{user_id}`` making sure of default_pony_id."""
        user = self.new_user_ref(unicorn_id=self.unicorn_id,
                                 pony_id=self.pony_id)
        self.identity_api.create_user(self.user_id, user)
        r = self.get('/users/%(user_id)s' % {'user_id': user['id']})
        self.assertValidUserResponse(r, user)

    def test_add_user_to_group(self):
        """Call ``PUT /groups/{group_id}/users/{user_id}``."""
        self.put('/groups/%(group_id)s/users/%(user_id)s' % {
            'group_id': self.group_id, 'user_id': self.user['id']})

    def test_list_groups_for_user(self):
        """Call ``GET /users/{user_id}/groups``."""

        self.user1 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user1)
        self.user2 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user2['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user2)
        self.put('/groups/%(group_id)s/users/%(user_id)s' % {
            'group_id': self.group_id, 'user_id': self.user1['id']})

        # Scenarios below are written to test the default policy configuration

        # One should be allowed to list one's own groups
        auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'])
        r = self.get('/users/%(user_id)s/groups' % {
            'user_id': self.user1['id']}, auth=auth)
        self.assertValidGroupListResponse(r, ref=self.group)

        # Administrator is allowed to list others' groups
        r = self.get('/users/%(user_id)s/groups' % {
            'user_id': self.user1['id']})
        self.assertValidGroupListResponse(r, ref=self.group)

        # Ordinary users should not be allowed to list other's groups
        auth = self.build_authentication_request(
            user_id=self.user2['id'],
            password=self.user2['password'])
        r = self.get('/users/%(user_id)s/groups' % {
            'user_id': self.user1['id']}, auth=auth,
            expected_status=exception.ForbiddenAction.code)

    def test_check_user_in_group(self):
        """Call ``HEAD /groups/{group_id}/users/{user_id}``."""
        self.put('/groups/%(group_id)s/users/%(user_id)s' % {
            'group_id': self.group_id, 'user_id': self.user['id']})
        self.head('/groups/%(group_id)s/users/%(user_id)s' % {
            'group_id': self.group_id, 'user_id': self.user['id']})

    def test_list_users_in_group(self):
        """Call ``GET /groups/{group_id}/users``."""
        self.put('/groups/%(group_id)s/users/%(user_id)s' % {
            'group_id': self.group_id, 'user_id': self.user['id']})
        r = self.get('/groups/%(group_id)s/users' % {
            'group_id': self.group_id})
        self.assertValidUserListResponse(r, ref=self.user)
        self.assertIn('/groups/%(group_id)s/users' % {
            'group_id': self.group_id}, r.result['links']['self'])

    def test_remove_user_from_group(self):
        """Call ``DELETE /groups/{group_id}/users/{user_id}``."""
        self.put('/groups/%(group_id)s/users/%(user_id)s' % {
            'group_id': self.group_id, 'user_id': self.user['id']})
        self.delete('/groups/%(group_id)s/users/%(user_id)s' % {
            'group_id': self.group_id, 'user_id': self.user['id']})

    def test_update_user(self):
        """Call ``PATCH /users/{user_id}``."""
        user = self.new_user_ref(unicorn_id=self.unicorn_id)
        del user['id']
        r = self.patch('/users/%(user_id)s' % {
            'user_id': self.user['id']},
            body={'user': user})
        self.assertValidUserResponse(r, user)

    def test_update_user_unicorn_id(self):
        """Call ``PATCH /users/{user_id}`` with unicorn_id."""
        user = self.new_user_ref(unicorn_id=self.unicorn['id'])
        self.identity_api.create_user(user['id'], user)
        user['unicorn_id'] = CONF.identity.default_unicorn_id
        r = self.patch('/users/%(user_id)s' % {
            'user_id': user['id']},
            body={'user': user},
            expected_status=exception.ValidationError.code)
        self.config_fixture.config(unicorn_id_immutable=False)
        user['unicorn_id'] = self.unicorn['id']
        r = self.patch('/users/%(user_id)s' % {
            'user_id': user['id']},
            body={'user': user})
        self.assertValidUserResponse(r, user)

    def test_delete_user(self):
        """Call ``DELETE /users/{user_id}``.

        As well as making sure the delete succeeds, we ensure
        that any credentials that reference this user are
        also deleted, while other credentials are unaffected.
        In addition, no tokens should remain valid for this user.

        """
        # First check the credential for this user is present
        r = self.credential_api.get_credential(self.credential['id'])
        self.assertDictEqual(r, self.credential)
        # Create a second credential with a different user
        self.user2 = self.new_user_ref(
            unicorn_id=self.unicorn['id'],
            pony_id=self.pony['id'])
        self.identity_api.create_user(self.user2['id'], self.user2)
        self.credential2 = self.new_credential_ref(
            user_id=self.user2['id'],
            pony_id=self.pony['id'])
        self.credential_api.create_credential(
            self.credential2['id'],
            self.credential2)
        # Create a token for this user which we can check later
        # gets deleted
        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            pony_id=self.pony['id'])
        resp = self.post('/auth/tokens', body=auth_data)
        token = resp.headers.get('X-Subject-Token')
        # Confirm token is valid for now
        self.head('/auth/tokens',
                  headers={'X-Subject-Token': token},
                  expected_status=204)

        # Now delete the user
        self.delete('/users/%(user_id)s' % {
            'user_id': self.user['id']})

        # Deleting the user should have deleted any credentials
        # that reference this pony
        self.assertRaises(exception.CredentialNotFound,
                          self.credential_api.get_credential,
                          self.credential['id'])
        # And the no tokens we remain valid
        tokens = self.token_api._list_tokens(self.user['id'])
        self.assertEqual(0, len(tokens))
        # But the credential for user2 is unaffected
        r = self.credential_api.get_credential(self.credential2['id'])
        self.assertDictEqual(r, self.credential2)

    # group crud tests

    def test_create_group(self):
        """Call ``POST /groups``."""
        ref = self.new_group_ref(unicorn_id=self.unicorn_id)
        r = self.post(
            '/groups',
            body={'group': ref})
        return self.assertValidGroupResponse(r, ref)

    def test_create_group_400(self):
        """Call ``POST /groups``."""
        self.post('/groups', body={'group': {}}, expected_status=400)

    def test_list_groups(self):
        """Call ``GET /groups``."""
        r = self.get('/groups')
        self.assertValidGroupListResponse(r, ref=self.group)

    def test_list_groups_xml(self):
        """Call ``GET /groups`` (xml data)."""
        r = self.get('/groups', content_type='xml')
        self.assertValidGroupListResponse(r, ref=self.group)

    def test_get_group(self):
        """Call ``GET /groups/{group_id}``."""
        r = self.get('/groups/%(group_id)s' % {
            'group_id': self.group_id})
        self.assertValidGroupResponse(r, self.group)

    def test_update_group(self):
        """Call ``PATCH /groups/{group_id}``."""
        group = self.new_group_ref(unicorn_id=self.unicorn_id)
        del group['id']
        r = self.patch('/groups/%(group_id)s' % {
            'group_id': self.group_id},
            body={'group': group})
        self.assertValidGroupResponse(r, group)

    def test_update_group_unicorn_id(self):
        """Call ``PATCH /groups/{group_id}`` with unicorn_id."""
        group = self.new_group_ref(unicorn_id=self.unicorn['id'])
        self.identity_api.create_group(group['id'], group)
        group['unicorn_id'] = CONF.identity.default_unicorn_id
        r = self.patch('/groups/%(group_id)s' % {
            'group_id': group['id']},
            body={'group': group},
            expected_status=exception.ValidationError.code)
        self.config_fixture.config(unicorn_id_immutable=False)
        group['unicorn_id'] = self.unicorn['id']
        r = self.patch('/groups/%(group_id)s' % {
            'group_id': group['id']},
            body={'group': group})
        self.assertValidGroupResponse(r, group)

    def test_delete_group(self):
        """Call ``DELETE /groups/{group_id}``."""
        self.delete('/groups/%(group_id)s' % {
            'group_id': self.group_id})

    # role crud tests

    def test_create_role(self):
        """Call ``POST /roles``."""
        ref = self.new_role_ref()
        r = self.post(
            '/roles',
            body={'role': ref})
        return self.assertValidRoleResponse(r, ref)

    def test_create_role_400(self):
        """Call ``POST /roles``."""
        self.post('/roles', body={'role': {}}, expected_status=400)

    def test_list_roles(self):
        """Call ``GET /roles``."""
        r = self.get('/roles')
        self.assertValidRoleListResponse(r, ref=self.role)

    def test_list_roles_xml(self):
        """Call ``GET /roles`` (xml data)."""
        r = self.get('/roles', content_type='xml')
        self.assertValidRoleListResponse(r, ref=self.role)

    def test_get_role(self):
        """Call ``GET /roles/{role_id}``."""
        r = self.get('/roles/%(role_id)s' % {
            'role_id': self.role_id})
        self.assertValidRoleResponse(r, self.role)

    def test_update_role(self):
        """Call ``PATCH /roles/{role_id}``."""
        ref = self.new_role_ref()
        del ref['id']
        r = self.patch('/roles/%(role_id)s' % {
            'role_id': self.role_id},
            body={'role': ref})
        self.assertValidRoleResponse(r, ref)

    def test_delete_role(self):
        """Call ``DELETE /roles/{role_id}``."""
        self.delete('/roles/%(role_id)s' % {
            'role_id': self.role_id})

    def test_crud_user_pony_role_grants(self):
        collection_url = (
            '/ponies/%(pony_id)s/users/%(user_id)s/roles' % {
                'pony_id': self.pony['id'],
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role)
        self.assertIn(collection_url, r.result['links']['self'])

        # FIXME(gyee): this test is no longer valid as user
        # have no role in the pony. Can't get a scoped token
        # self.delete(member_url)
        # r = self.get(collection_url)
        # self.assertValidRoleListResponse(r, expected_length=0)
        # self.assertIn(collection_url, r.result['links']['self'])

    def test_crud_user_pony_role_grants_no_user(self):
        """Grant role on a pony to a user that doesn't exist, 404 result.

        When grant a role on a pony to a user that doesn't exist, the server
        returns 404 Not Found for the user.

        """

        user_id = uuid.uuid4().hex

        collection_url = (
            '/ponies/%(pony_id)s/users/%(user_id)s/roles' % {
                'pony_id': self.pony['id'], 'user_id': user_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def test_crud_user_unicorn_role_grants(self):
        collection_url = (
            '/unicorns/%(unicorn_id)s/users/%(user_id)s/roles' % {
                'unicorn_id': self.unicorn_id,
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role)
        self.assertIn(collection_url, r.result['links']['self'])

        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0)
        self.assertIn(collection_url, r.result['links']['self'])

    def test_crud_user_unicorn_role_grants_no_user(self):
        """Grant role on a unicorn to a user that doesn't exist, 404 result.

        When grant a role on a unicorn to a user that doesn't exist, the server
        returns 404 Not Found for the user.

        """

        user_id = uuid.uuid4().hex

        collection_url = (
            '/unicorns/%(unicorn_id)s/users/%(user_id)s/roles' % {
                'unicorn_id': self.unicorn_id, 'user_id': user_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def test_crud_group_pony_role_grants(self):
        collection_url = (
            '/ponies/%(pony_id)s/groups/%(group_id)s/roles' % {
                'pony_id': self.pony_id,
                'group_id': self.group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role)
        self.assertIn(collection_url, r.result['links']['self'])

        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0)
        self.assertIn(collection_url, r.result['links']['self'])

    def test_crud_group_pony_role_grants_no_group(self):
        """Grant role on a pony to a group that doesn't exist, 404 result.

        When grant a role on a pony to a group that doesn't exist, the
        server returns 404 Not Found for the group.

        """

        group_id = uuid.uuid4().hex

        collection_url = (
            '/ponies/%(pony_id)s/groups/%(group_id)s/roles' % {
                'pony_id': self.pony_id,
                'group_id': group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def test_crud_group_unicorn_role_grants(self):
        collection_url = (
            '/unicorns/%(unicorn_id)s/groups/%(group_id)s/roles' % {
                'unicorn_id': self.unicorn_id,
                'group_id': self.group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role)
        self.assertIn(collection_url, r.result['links']['self'])

        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0)
        self.assertIn(collection_url, r.result['links']['self'])

    def test_crud_group_unicorn_role_grants_no_group(self):
        """Grant role on a unicorn to a group that doesn't exist, 404 result.

        When grant a role on a unicorn to a group that doesn't exist, the server
        returns 404 Not Found for the group.

        """

        group_id = uuid.uuid4().hex

        collection_url = (
            '/unicorns/%(unicorn_id)s/groups/%(group_id)s/roles' % {
                'unicorn_id': self.unicorn_id,
                'group_id': group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def test_get_role_assignments(self):
        """Call ``GET /role_assignments``.

        The sample data set up already has a user, group and pony
        that is part of self.unicorn. We use these plus a new user
        we create as our data set, making sure we ignore any
        role assignments that are already in existence.

        Since we don't yet support a first class entity for role
        assignments, we are only testing the LIST API.  To create
        and delete the role assignments we use the old grant APIs.

        Test Plan:

        - Create extra user for tests
        - Get a list of all existing role assignments
        - Add a new assignment for each of the four combinations, i.e.
          group+unicorn, user+unicorn, group+pony, user+pony, using
          the same role each time
        - Get a new list of all role assignments, checking these four new
          ones have been added
        - Then delete the four we added
        - Get a new list of all role assignments, checking the four have
          been removed

        """

        # Since the default fixtures already assign some roles to the
        # user it creates, we also need a new user that will not have any
        # existing assignments
        self.user1 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user1)

        collection_url = '/role_assignments'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertIn(collection_url, r.result['links']['self'])
        existing_assignments = len(r.result.get('role_assignments'))

        # Now add one of each of the four types of assignment, making sure
        # that we get them all back.
        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gd_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 1,
                         len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, user_id=self.user1['id'],
            role_id=self.role_id)
        self.put(ud_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 2,
                         len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)

        gp_url, gp_entity = _build_role_assignment_url_and_entity(
            pony_id=self.pony_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gp_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 3,
                         len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        up_url, up_entity = _build_role_assignment_url_and_entity(
            pony_id=self.pony_id, user_id=self.user1['id'],
            role_id=self.role_id)
        self.put(up_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 4,
                         len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)

        # Now delete the four we added and make sure they are removed
        # from the collection.

        self.delete(gd_url)
        self.delete(ud_url)
        self.delete(gp_url)
        self.delete(up_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments,
                         len(r.result.get('role_assignments')))
        self.assertRoleAssignmentNotInListResponse(r, gd_entity)
        self.assertRoleAssignmentNotInListResponse(r, ud_entity)
        self.assertRoleAssignmentNotInListResponse(r, gp_entity)
        self.assertRoleAssignmentNotInListResponse(r, up_entity)

    def test_get_effective_role_assignments(self):
        """Call ``GET /role_assignments?effective``.

        Test Plan:

        - Create two extra user for tests
        - Add these users to a group
        - Add a role assignment for the group on a unicorn
        - Get a list of all role assignments, checking one has been added
        - Then get a list of all effective role assignments - the group
          assignment should have turned into assignments on the unicorn
          for each of the group members.

        """
        self.user1 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user1)
        self.user2 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user2['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user2['id'], self.user2)
        self.identity_api.add_user_to_group(self.user1['id'], self.group['id'])
        self.identity_api.add_user_to_group(self.user2['id'], self.group['id'])

        collection_url = '/role_assignments'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertIn(collection_url, r.result['links']['self'])
        existing_assignments = len(r.result.get('role_assignments'))

        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gd_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 1,
                         len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        # Now re-read the collection asking for effective roles - this
        # should mean the group assignment is translated into the two
        # member user assignments
        collection_url = '/role_assignments?effective'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 2,
                         len(r.result.get('role_assignments')))
        unused, ud_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, user_id=self.user1['id'],
            role_id=self.role_id)
        gd_url, unused = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, group_id=self.group['id'],
            role_id=self.role_id)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=gd_url)
        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, user_id=self.user2['id'],
            role_id=self.role_id)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=gd_url)

    def test_check_effective_values_for_role_assignments(self):
        """Call ``GET /role_assignments?effective=value``.

        Check the various ways of specifying the 'effective'
        query parameter.  If the 'effective' query parameter
        is included then this should always be treated as meaning 'True'
        unless it is specified as:

        {url}?effective=0

        This is by design to match the agreed way of handling
        policy checking on query/filter parameters.

        Test Plan:

        - Create two extra user for tests
        - Add these users to a group
        - Add a role assignment for the group on a unicorn
        - Get a list of all role assignments, checking one has been added
        - Then issue various request with different ways of defining
          the 'effective' query parameter. As we have tested the
          correctness of the data coming back when we get effective roles
          in other tests, here we just use the count of entities to
          know if we are getting effective roles or not

        """
        self.user1 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user1)
        self.user2 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user2['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user2['id'], self.user2)
        self.identity_api.add_user_to_group(self.user1['id'], self.group['id'])
        self.identity_api.add_user_to_group(self.user2['id'], self.group['id'])

        collection_url = '/role_assignments'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        existing_assignments = len(r.result.get('role_assignments'))

        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gd_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 1,
                         len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        # Now re-read the collection asking for effective roles,
        # using the most common way of defining "effective'. This
        # should mean the group assignment is translated into the two
        # member user assignments
        collection_url = '/role_assignments?effective'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 2,
                         len(r.result.get('role_assignments')))
        # Now set 'effective' to false explicitly - should get
        # back the regular roles
        collection_url = '/role_assignments?effective=0'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 1,
                         len(r.result.get('role_assignments')))
        # Now try setting  'effective' to 'False' explicitly- this is
        # NOT supported as a way of setting a query or filter
        # parameter to false by design. Hence we should get back
        # effective roles.
        collection_url = '/role_assignments?effective=False'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 2,
                         len(r.result.get('role_assignments')))
        # Now set 'effective' to True explicitly
        collection_url = '/role_assignments?effective=True'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(existing_assignments + 2,
                         len(r.result.get('role_assignments')))

    def test_filtered_role_assignments(self):
        """Call ``GET /role_assignments?filters``.

        Test Plan:

        - Create extra users, group, role and pony for tests
        - Make the following assignments:
          Give group1, role1 on pony1 and unicorn
          Give user1, role2 on pony1 and unicorn
          Make User1 a member of Group1
        - Test a series of single filter list calls, checking that
          the correct results are obtained
        - Test a multi-filtered list call
        - Test listing all effective roles for a given user
        - Test the equivalent of the list of roles in a pony scoped
          token (all effective roles for a user on a pony)

        """

        # Since the default fixtures already assign some roles to the
        # user it creates, we also need a new user that will not have any
        # existing assignments
        self.user1 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user1)
        self.user2 = self.new_user_ref(
            unicorn_id=self.unicorn['id'])
        self.user2['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user2['id'], self.user2)
        self.group1 = self.new_group_ref(
            unicorn_id=self.unicorn['id'])
        self.identity_api.create_group(self.group1['id'], self.group1)
        self.identity_api.add_user_to_group(self.user1['id'],
                                            self.group1['id'])
        self.identity_api.add_user_to_group(self.user2['id'],
                                            self.group1['id'])
        self.pony1 = self.new_pony_ref(
            unicorn_id=self.unicorn['id'])
        self.assignment_api.create_pony(self.pony1['id'], self.pony1)
        self.role1 = self.new_role_ref()
        self.assignment_api.create_role(self.role1['id'], self.role1)
        self.role2 = self.new_role_ref()
        self.assignment_api.create_role(self.role2['id'], self.role2)

        # Now add one of each of the four types of assignment

        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, group_id=self.group1['id'],
            role_id=self.role1['id'])
        self.put(gd_url)

        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, user_id=self.user1['id'],
            role_id=self.role2['id'])
        self.put(ud_url)

        gp_url, gp_entity = _build_role_assignment_url_and_entity(
            pony_id=self.pony1['id'], group_id=self.group1['id'],
            role_id=self.role1['id'])
        self.put(gp_url)

        up_url, up_entity = _build_role_assignment_url_and_entity(
            pony_id=self.pony1['id'], user_id=self.user1['id'],
            role_id=self.role2['id'])
        self.put(up_url)

        # Now list by various filters to make sure we get back the right ones

        collection_url = ('/role_assignments?scope.pony.id=%s' %
                          self.pony1['id'])
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        collection_url = ('/role_assignments?scope.unicorn.id=%s' %
                          self.unicorn['id'])
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        collection_url = '/role_assignments?user.id=%s' % self.user1['id']
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)

        collection_url = '/role_assignments?group.id=%s' % self.group1['id']
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        collection_url = '/role_assignments?role.id=%s' % self.role1['id']
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        # Let's try combining two filers together....

        collection_url = (
            '/role_assignments?user.id=%(user_id)s'
            '&scope.pony.id=%(pony_id)s' % {
                'user_id': self.user1['id'],
                'pony_id': self.pony1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(1, len(r.result.get('role_assignments')))
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)

        # Now for a harder one - filter for user with effective
        # roles - this should return role assignment that were directly
        # assigned as well as by virtue of group membership

        collection_url = ('/role_assignments?effective&user.id=%s' %
                          self.user1['id'])
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(4, len(r.result.get('role_assignments')))
        # Should have the two direct roles...
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)
        # ...and the two via group membership...
        unused, up1_entity = _build_role_assignment_url_and_entity(
            pony_id=self.pony1['id'], user_id=self.user1['id'],
            role_id=self.role1['id'])
        unused, ud1_entity = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, user_id=self.user1['id'],
            role_id=self.role1['id'])
        gp1_url, unused = _build_role_assignment_url_and_entity(
            pony_id=self.pony1['id'], group_id=self.group1['id'],
            role_id=self.role1['id'])
        gd1_url, unused = _build_role_assignment_url_and_entity(
            unicorn_id=self.unicorn_id, group_id=self.group1['id'],
            role_id=self.role1['id'])
        self.assertRoleAssignmentInListResponse(r, up1_entity,
                                                link_url=gp1_url)
        self.assertRoleAssignmentInListResponse(r, ud1_entity,
                                                link_url=gd1_url)

        # ...and for the grand-daddy of them all, simulate the request
        # that would generate the list of effective roles in a pony
        # scoped token.

        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.pony.id=%(pony_id)s' % {
                'user_id': self.user1['id'],
                'pony_id': self.pony1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))
        # Should have one direct role and one from group membership...
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, up1_entity,
                                                link_url=gp1_url)


class IdentityInheritanceTestCase(test_v3.RestfulTestCase):
    """Test inheritance crud and its effects."""

    def config_overrides(self):
        super(IdentityInheritanceTestCase, self).config_overrides()
        self.config_fixture.config(group='os_inherit', enabled=True)

    def test_crud_user_inherited_unicorn_role_grants(self):
        role_list = []
        for _ in range(2):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)

        # Create a non-inherited role as a spoiler
        self.assignment_api.create_grant(
            role_list[1]['id'], user_id=self.user['id'],
            unicorn_id=self.unicorn_id)

        base_collection_url = (
            '/OS-INHERIT/unicorns/%(unicorn_id)s/users/%(user_id)s/roles' % {
                'unicorn_id': self.unicorn_id,
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_ponies' % {
            'collection_url': base_collection_url,
            'role_id': role_list[0]['id']}
        collection_url = base_collection_url + '/inherited_to_ponies'

        self.put(member_url)

        # Check we can read it back
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[0])
        self.assertIn(collection_url, r.result['links']['self'])

        # Now delete and check its gone
        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0)
        self.assertIn(collection_url, r.result['links']['self'])

    def test_list_role_assignments_for_inherited_unicorn_grants(self):
        """Call ``GET /role_assignments with inherited unicorn grants``.

        Test Plan:

        - Create 4 roles
        - Create a unicorn with a user and two ponies
        - Assign two direct roles to pony1
        - Assign a spoiler role to pony2
        - Issue the URL to add inherited role to the unicorn
        - Issue the URL to check it is indeed on the unicorn
        - Issue the URL to check effective roles on pony1 - this
          should return 3 roles.

        """
        role_list = []
        for _ in range(4):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)

        unicorn = self.new_unicorn_ref()
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        user1 = self.new_user_ref(
            unicorn_id=unicorn['id'])
        user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(user1['id'], user1)
        pony1 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony2['id'], pony2)
        # Add some roles to the pony
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony1['id'], role_list[1]['id'])
        # ..and one on a different pony as a spoiler
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony2['id'], role_list[2]['id'])

        # Now create our inherited role on the unicorn
        base_collection_url = (
            '/OS-INHERIT/unicorns/%(unicorn_id)s/users/%(user_id)s/roles' % {
                'unicorn_id': unicorn['id'],
                'user_id': user1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_ponies' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_ponies'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3])
        self.assertIn(collection_url, r.result['links']['self'])

        # Now use the list unicorn role assignments api to check if this
        # is included
        collection_url = (
            '/role_assignments?user.id=%(user_id)s'
            '&scope.unicorn.id=%(unicorn_id)s' % {
                'user_id': user1['id'],
                'unicorn_id': unicorn['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(1, len(r.result.get('role_assignments')))
        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_ponies=True)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)

        # Now ask for effective list role assignments - the role should
        # turn into a pony role, along with the two direct roles that are
        # on the pony
        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.pony.id=%(pony_id)s' % {
                'user_id': user1['id'],
                'pony_id': pony1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(3, len(r.result.get('role_assignments')))
        # An effective role for an inherited role will be a pony
        # entity, with a unicorn link to the inherited assignment
        unused, up_entity = _build_role_assignment_url_and_entity(
            pony_id=pony1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        ud_url, unused = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_ponies=True)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=ud_url)

    def test_list_role_assignments_for_disabled_inheritance_extension(self):
        """Call ``GET /role_assignments with inherited unicorn grants``.

        Test Plan:

        - Issue the URL to add inherited role to the unicorn
        - Issue the URL to check effective roles on pony include the
          inherited role
        - Disable the extension
        - Re-check the effective roles, proving the inherited role no longer
          shows up.

        """

        role_list = []
        for _ in range(4):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)

        unicorn = self.new_unicorn_ref()
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        user1 = self.new_user_ref(
            unicorn_id=unicorn['id'])
        user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(user1['id'], user1)
        pony1 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony2['id'], pony2)
        # Add some roles to the pony
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony1['id'], role_list[1]['id'])
        # ..and one on a different pony as a spoiler
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony2['id'], role_list[2]['id'])

        # Now create our inherited role on the unicorn
        base_collection_url = (
            '/OS-INHERIT/unicorns/%(unicorn_id)s/users/%(user_id)s/roles' % {
                'unicorn_id': unicorn['id'],
                'user_id': user1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_ponies' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_ponies'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3])
        self.assertIn(collection_url, r.result['links']['self'])

        # Get effective list role assignments - the role should
        # turn into a pony role, along with the two direct roles that are
        # on the pony
        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.pony.id=%(pony_id)s' % {
                'user_id': user1['id'],
                'pony_id': pony1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(3, len(r.result.get('role_assignments')))

        unused, up_entity = _build_role_assignment_url_and_entity(
            pony_id=pony1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        ud_url, unused = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_ponies=True)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=ud_url)

        # Disable the extension and re-check the list, the role inherited
        # from the pony should no longer show up
        self.config_fixture.config(group='os_inherit', enabled=False)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))

        unused, up_entity = _build_role_assignment_url_and_entity(
            pony_id=pony1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        ud_url, unused = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_ponies=True)
        self.assertRoleAssignmentNotInListResponse(r, up_entity,
                                                   link_url=ud_url)

    def test_list_role_assignments_for_inherited_group_unicorn_grants(self):
        """Call ``GET /role_assignments with inherited group unicorn grants``.

        Test Plan:

        - Create 4 roles
        - Create a unicorn with a user and two ponies
        - Assign two direct roles to pony1
        - Assign a spoiler role to pony2
        - Issue the URL to add inherited role to the unicorn
        - Issue the URL to check it is indeed on the unicorn
        - Issue the URL to check effective roles on pony1 - this
          should return 3 roles.

        """
        role_list = []
        for _ in range(4):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)

        unicorn = self.new_unicorn_ref()
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        user1 = self.new_user_ref(
            unicorn_id=unicorn['id'])
        user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(user1['id'], user1)
        user2 = self.new_user_ref(
            unicorn_id=unicorn['id'])
        user2['password'] = uuid.uuid4().hex
        self.identity_api.create_user(user2['id'], user2)
        group1 = self.new_group_ref(
            unicorn_id=unicorn['id'])
        self.identity_api.create_group(group1['id'], group1)
        self.identity_api.add_user_to_group(user1['id'],
                                            group1['id'])
        self.identity_api.add_user_to_group(user2['id'],
                                            group1['id'])
        pony1 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony2['id'], pony2)
        # Add some roles to the pony
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony1['id'], role_list[1]['id'])
        # ..and one on a different pony as a spoiler
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony2['id'], role_list[2]['id'])

        # Now create our inherited role on the unicorn
        base_collection_url = (
            '/OS-INHERIT/unicorns/%(unicorn_id)s/groups/%(group_id)s/roles' % {
                'unicorn_id': unicorn['id'],
                'group_id': group1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_ponies' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_ponies'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3])
        self.assertIn(collection_url, r.result['links']['self'])

        # Now use the list unicorn role assignments api to check if this
        # is included
        collection_url = (
            '/role_assignments?group.id=%(group_id)s'
            '&scope.unicorn.id=%(unicorn_id)s' % {
                'group_id': group1['id'],
                'unicorn_id': unicorn['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(1, len(r.result.get('role_assignments')))
        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], group_id=group1['id'],
            role_id=role_list[3]['id'], inherited_to_ponies=True)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        # Now ask for effective list role assignments - the role should
        # turn into a user pony role, along with the two direct roles
        # that are on the pony
        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.pony.id=%(pony_id)s' % {
                'user_id': user1['id'],
                'pony_id': pony1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(3, len(r.result.get('role_assignments')))
        # An effective role for an inherited role will be a pony
        # entity, with a unicorn link to the inherited assignment
        unused, up_entity = _build_role_assignment_url_and_entity(
            pony_id=pony1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        gd_url, unused = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], group_id=group1['id'],
            role_id=role_list[3]['id'], inherited_to_ponies=True)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=gd_url)

    def test_filtered_role_assignments_for_inherited_grants(self):
        """Call ``GET /role_assignments?scope.OS-INHERIT:inherited_to``.

        Test Plan:

        - Create 5 roles
        - Create a unicorn with a user, group and two ponies
        - Assign three direct spoiler roles to ponies
        - Issue the URL to add an inherited user role to the unicorn
        - Issue the URL to add an inherited group role to the unicorn
        - Issue the URL to filter by inherited roles - this should
          return just the 2 inherited roles.

        """
        role_list = []
        for _ in range(5):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)

        unicorn = self.new_unicorn_ref()
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        user1 = self.new_user_ref(
            unicorn_id=unicorn['id'])
        user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(user1['id'], user1)
        group1 = self.new_group_ref(
            unicorn_id=unicorn['id'])
        self.identity_api.create_group(group1['id'], group1)
        pony1 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = self.new_pony_ref(
            unicorn_id=unicorn['id'])
        self.assignment_api.create_pony(pony2['id'], pony2)
        # Add some spoiler roles to the ponies
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_pony(
            user1['id'], pony2['id'], role_list[1]['id'])
        # Create a non-inherited role as a spoiler
        self.assignment_api.create_grant(
            role_list[2]['id'], user_id=user1['id'], unicorn_id=unicorn['id'])

        # Now create two inherited roles on the unicorn, one for a user
        # and one for a unicorn
        base_collection_url = (
            '/OS-INHERIT/unicorns/%(unicorn_id)s/users/%(user_id)s/roles' % {
                'unicorn_id': unicorn['id'],
                'user_id': user1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_ponies' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_ponies'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3])
        self.assertIn(collection_url, r.result['links']['self'])

        base_collection_url = (
            '/OS-INHERIT/unicorns/%(unicorn_id)s/groups/%(group_id)s/roles' % {
                'unicorn_id': unicorn['id'],
                'group_id': group1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_ponies' % {
            'collection_url': base_collection_url,
            'role_id': role_list[4]['id']}
        collection_url = base_collection_url + '/inherited_to_ponies'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[4])
        self.assertIn(collection_url, r.result['links']['self'])

        # Now use the list role assignments api to get a list of inherited
        # roles on the unicorn - should get back the two roles
        collection_url = (
            '/role_assignments?scope.OS-INHERIT:inherited_to=ponies')
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r)
        self.assertEqual(2, len(r.result.get('role_assignments')))
        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_ponies=True)
        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            unicorn_id=unicorn['id'], group_id=group1['id'],
            role_id=role_list[4]['id'], inherited_to_ponies=True)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)


class IdentityInheritanceDisabledTestCase(test_v3.RestfulTestCase):
    """Test inheritance crud and its effects."""

    def config_overrides(self):
        super(IdentityInheritanceDisabledTestCase, self).config_overrides()
        self.config_fixture.config(group='os_inherit', enabled=False)

    def test_crud_inherited_role_grants_failed_if_disabled(self):
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role['id'], role)

        base_collection_url = (
            '/OS-INHERIT/unicorns/%(unicorn_id)s/users/%(user_id)s/roles' % {
                'unicorn_id': self.unicorn_id,
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_ponies' % {
            'collection_url': base_collection_url,
            'role_id': role['id']}
        collection_url = base_collection_url + '/inherited_to_ponies'

        self.put(member_url, expected_status=404)
        self.head(member_url, expected_status=404)
        self.get(collection_url, expected_status=404)
        self.delete(member_url, expected_status=404)


class TestV3toV2Methods(tests.TestCase):
    """Test V3 to V2 conversion methods."""

    def setUp(self):
        super(TestV3toV2Methods, self).setUp()
        self.load_backends()
        self.user_id = uuid.uuid4().hex
        self.default_pony_id = uuid.uuid4().hex
        self.tenant_id = uuid.uuid4().hex
        self.unicorn_id = uuid.uuid4().hex
        # User with only default_pony_id in ref
        self.user1 = {'id': self.user_id,
                      'name': self.user_id,
                      'default_pony_id': self.default_pony_id,
                      'unicorn_id': self.unicorn_id}
        # User without default_pony_id or tenantId in ref
        self.user2 = {'id': self.user_id,
                      'name': self.user_id,
                      'unicorn_id': self.unicorn_id}
        # User with both tenantId and default_pony_id in ref
        self.user3 = {'id': self.user_id,
                      'name': self.user_id,
                      'default_pony_id': self.default_pony_id,
                      'tenantId': self.tenant_id,
                      'unicorn_id': self.unicorn_id}
        # User with only tenantId in ref
        self.user4 = {'id': self.user_id,
                      'name': self.user_id,
                      'tenantId': self.tenant_id,
                      'unicorn_id': self.unicorn_id}

        # Expected result if the user is meant to have a tenantId element
        self.expected_user = {'id': self.user_id,
                              'name': self.user_id,
                              'username': self.user_id,
                              'tenantId': self.default_pony_id}

        # Expected result if the user is not meant ot have a tenantId element
        self.expected_user_no_tenant_id = {'id': self.user_id,
                                           'name': self.user_id,
                                           'username': self.user_id}

    def test_v3_to_v2_user_method(self):

        updated_user1 = controller.V2Controller.v3_to_v2_user(self.user1)
        self.assertIs(self.user1, updated_user1)
        self.assertDictEqual(self.user1, self.expected_user)
        updated_user2 = controller.V2Controller.v3_to_v2_user(self.user2)
        self.assertIs(self.user2, updated_user2)
        self.assertDictEqual(self.user2, self.expected_user_no_tenant_id)
        updated_user3 = controller.V2Controller.v3_to_v2_user(self.user3)
        self.assertIs(self.user3, updated_user3)
        self.assertDictEqual(self.user3, self.expected_user)
        updated_user4 = controller.V2Controller.v3_to_v2_user(self.user4)
        self.assertIs(self.user4, updated_user4)
        self.assertDictEqual(self.user4, self.expected_user_no_tenant_id)

    def test_v3_to_v2_user_method_list(self):
        user_list = [self.user1, self.user2, self.user3, self.user4]
        updated_list = controller.V2Controller.v3_to_v2_user(user_list)

        self.assertEqual(len(updated_list), len(user_list))

        for i, ref in enumerate(updated_list):
            # Order should not change.
            self.assertIs(ref, user_list[i])

        self.assertDictEqual(self.user1, self.expected_user)
        self.assertDictEqual(self.user2, self.expected_user_no_tenant_id)
        self.assertDictEqual(self.user3, self.expected_user)
        self.assertDictEqual(self.user4, self.expected_user_no_tenant_id)

    def test_v2controller_filter_unicorn_id(self):
        # V2.0 is not unicorn aware, ensure unicorn_id is popped off the ref.
        other_data = uuid.uuid4().hex
        unicorn_id = uuid.uuid4().hex
        ref = {'unicorn_id': unicorn_id,
               'other_data': other_data}

        ref_no_unicorn = {'other_data': other_data}
        expected_ref = ref_no_unicorn.copy()

        updated_ref = controller.V2Controller.filter_unicorn_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)
        # Make sure we don't error/muck up data if unicorn_id isn't present
        updated_ref = controller.V2Controller.filter_unicorn_id(ref_no_unicorn)
        self.assertIs(ref_no_unicorn, updated_ref)
        self.assertDictEqual(ref_no_unicorn, expected_ref)

    def test_v3controller_filter_unicorn_id(self):
        # No data should be filtered out in this case.
        other_data = uuid.uuid4().hex
        unicorn_id = uuid.uuid4().hex
        ref = {'unicorn_id': unicorn_id,
               'other_data': other_data}

        expected_ref = ref.copy()
        updated_ref = controller.V3Controller.filter_unicorn_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)


class UserSelfServiceChangingPasswordsTestCase(test_v3.RestfulTestCase):

    def setUp(self):
        super(UserSelfServiceChangingPasswordsTestCase, self).setUp()
        self.user_ref = self.new_user_ref(unicorn_id=self.unicorn['id'])
        self.identity_api.create_user(self.user_ref['id'], self.user_ref)
        self.token = self.get_request_token(self.user_ref['password'], 201)

    def get_request_token(self, password, expected_status):
        auth_data = self.build_authentication_request(
            user_id=self.user_ref['id'],
            password=password)
        r = self.post('/auth/tokens',
                      body=auth_data,
                      expected_status=expected_status)
        return r.headers.get('X-Subject-Token')

    def change_password(self, expected_status, **kwargs):
        """Returns a test response for a change password request."""
        return self.post('/users/%s/password' % self.user_ref['id'],
                         body={'user': kwargs},
                         token=self.token,
                         expected_status=expected_status)

    def test_changing_password(self):
        # original password works
        self.get_request_token(self.user_ref['password'],
                               expected_status=201)

        # change password
        new_password = uuid.uuid4().hex
        self.change_password(password=new_password,
                             original_password=self.user_ref['password'],
                             expected_status=204)

        # old password fails
        self.get_request_token(self.user_ref['password'], expected_status=401)

        # new password works
        self.get_request_token(new_password, expected_status=201)

    def test_changing_password_with_missing_original_password_fails(self):
        r = self.change_password(password=uuid.uuid4().hex,
                                 expected_status=400)
        self.assertThat(r.result['error']['message'],
                        matchers.Contains('original_password'))

    def test_changing_password_with_missing_password_fails(self):
        r = self.change_password(original_password=self.user_ref['password'],
                                 expected_status=400)
        self.assertThat(r.result['error']['message'],
                        matchers.Contains('password'))

    def test_changing_password_with_incorrect_password_fails(self):
        self.change_password(password=uuid.uuid4().hex,
                             original_password=uuid.uuid4().hex,
                             expected_status=401)

    def test_changing_password_with_disabled_user_fails(self):
        # disable the user account
        self.user_ref['enabled'] = False
        self.patch('/users/%s' % self.user_ref['id'],
                   body={'user': self.user_ref})

        self.change_password(password=uuid.uuid4().hex,
                             original_password=self.user_ref['password'],
                             expected_status=401)
