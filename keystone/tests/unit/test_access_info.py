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

from datetime import datetime
import os
import uuid

from oslo_serialization import jsonutils
from oslo_utils import timeutils
import six
import testtools

from keystone.models import access_info
from keystone.models import builder
from keystoneclient.tests.unit import client_fixtures


class AccessTestCase(testtools.TestCase):

    def setUp(self):
        super(AccessTestCase, self).setUp()

        self.dom_id = uuid.uuid4().hex
        self.user_id = uuid.uuid4().hex

    def test_create_user(self):
        domain = access_info.Domain(self.dom_id, uuid.uuid4().hex)
        user = access_info.User(self.user_id, uuid.uuid4().hex, domain)
        self.assertEqual(user['id'], self.user_id)
        self.assertEqual(user['domain']['id'], self.dom_id)

    def test_class(self):
        try:
            access_info.Role('u2', 4)
            self.fail()
        except ValueError:
            pass

    def test_immutable(self):
        try:
            domain = access_info.Domain('id', 'name')
            domain.lock()
            domain.name = "should not work"
            self.fail()
        except AttributeError:
            pass

    def test_builder_unscoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_unscoped)
        self.assertIsNotNone(access)
        self.assert_deep_match(access_data_unscoped['token'], access)

    def test_builder_project_scoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_project_scoped)
        self.assertIsNotNone(access)
        self.assert_deep_match(access_data_project_scoped['token'], access)

    def test_builder_domain_scoped_domain(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_domain_scoped)
        self.assertIsNotNone(access)

    def assert_list_match(self, first, second):
        index = 0
        a = []
        b = []

        for item in first:
            if isinstance(item, six.string_types):
                a.append(item)
                b.append(second[index])
            else:
                a.append(item['id'])
                b.append(second[index]['id'])
            index += 1

        a.sort()
        b.sort()
        for i in range(0, len(a)):
            self.assertEqual(a[i], b[i])

    def assert_catalog_match(self, first, second):
        for i in range(0, len(first)):
            self.assert_list_match(first[i]['endpoints'],
                                   second[i]['endpoints'])

    def assert_deep_match(self, first, second):
        for k, v in six.iteritems(first):
            if isinstance(v, six.string_types):
                if isinstance(v, access_info.DateString):
                    self.assertEqual(v, second[k])
                elif isinstance(second[k], datetime):
                    date_v = timeutils.parse_isotime(v)
                    self.assertEqual(date_v, second[k])
                else:
                    self.assertEqual(v, second[k])
            elif k == 'catalog':
                self.assert_catalog_match(v, second[k])
            elif isinstance(v, list):
                try:
                    self.assert_list_match(v, second[k])
                except KeyError:
                    print('failed testing %s' % k)
                    raise
            else:
                self.assert_deep_match(v, second[k])

    def _user_domain(self):
        dom_data = access_data_unscoped['token']['user']['domain']
        domain = access_info.Domain(dom_data['id'], dom_data['name'])

        return domain

    def test_encode_domain(self):
        encoded = jsonutils.loads(jsonutils.dumps(self._user_domain()))
        self.assert_deep_match(
            encoded,
            access_data_domain_scoped['token']['user']['domain'])

    def test_encode_user(self):
        user_data = access_data_unscoped['token']['user']
        user = access_info.User(user_data['id'], user_data['name'],
                                self._user_domain())
        encoded = jsonutils.loads(jsonutils.dumps(user))
        self.assert_deep_match(encoded,
                               access_data_unscoped['token']['user'])

    def test_encode_datestring(self):
        expires_at_datetime = timeutils.parse_isotime(
            access_data_unscoped['token']['expires_at'])
        expires_at = access_info.DateString(expires_at_datetime)
        jsonutils.dumps(expires_at)

    def test_encode_unscoped(self):

        director = builder.PythonDirector()
        access = director.construct(access_data_unscoped)
        jsonutils.dumps(access)
        self.assertEqual(access.user.id,
                         access_data_unscoped['token']['user']['id'])

    def test_encode_domain_scoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_domain_scoped)
        jsonutils.dumps(access)
        self.assertEqual(access.domain.id,
                         access_data_domain_scoped['token']['domain']['id'])
        self.assertEqual(access.audit_ids,
                         access_data_domain_scoped['token']['audit_ids'])

    def test_encode_project_scoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_project_scoped)
        jsonutils.dumps(access)
        self.assertEqual(access.project.id,
                         access_data_project_scoped['token']['project']['id'])
        self.assertEqual(access.audit_ids,
                         access_data_project_scoped['token']['audit_ids'])

    def test_encode_v2_scoped(self):
        with open(os.path.join(client_fixtures.CMSDIR,
                               'auth_token_v2_scoped.json')) as f:
            access_data_v2_scoped = jsonutils.loads(f.read())

        director = builder.PythonDirector()
        access = director.construct(access_data_v2_scoped)
        jsonutils.dumps(access)
        self.assertEqual(access.project.id, 'tenant_id1')
        self.assertEqual(access.audit_ids,
                         access_data_v2_scoped['access']['token']['audit_ids'])


with open(os.path.join(client_fixtures.CMSDIR,
                       'auth_v3_token_unscoped.json')) as f:
    access_data_unscoped = jsonutils.loads(f.read())


with open(os.path.join(client_fixtures.CMSDIR,
                       'auth_v3_token_project_scoped.json')) as f:
    access_data_project_scoped = jsonutils.loads(f.read())


with open(os.path.join(client_fixtures.CMSDIR,
                       'auth_v3_token_domain_scoped.json')) as f:
    access_data_domain_scoped = jsonutils.loads(f.read())
