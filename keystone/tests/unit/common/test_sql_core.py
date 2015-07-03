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


from sqlalchemy.ext import declarative

from keystone.common import sql
from keystone.tests import unit as tests
from keystone.tests.unit import default_fixtures
from keystone.tests.unit import utils
from keystone.tests.unit.ksfixtures import database


ModelBase = declarative.declarative_base()


class TestModel(ModelBase, sql.ModelDictMixin):
    __tablename__ = 'testmodel'
    id = sql.Column(sql.String(64), primary_key=True)
    text = sql.Column(sql.String(64), nullable=False)


class TestModelDictMixin(tests.BaseTestCase):

    def test_creating_a_model_instance_from_a_dict(self):
        d = {'id': utils.new_uuid(), 'text': utils.new_uuid()}
        m = TestModel.from_dict(d)
        self.assertEqual(m.id, d['id'])
        self.assertEqual(m.text, d['text'])

    def test_creating_a_dict_from_a_model_instance(self):
        m = TestModel(id=utils.new_uuid(), text=utils.new_uuid())
        d = m.to_dict()
        self.assertEqual(m.id, d['id'])
        self.assertEqual(m.text, d['text'])

    def test_creating_a_model_instance_from_an_invalid_dict(self):
        d = {'id': utils.new_uuid(), 'text': utils.new_uuid(), 'extra': None}
        self.assertRaises(TypeError, TestModel.from_dict, d)

    def test_creating_a_dict_from_a_model_instance_that_has_extra_attrs(self):
        expected = {'id': utils.new_uuid(), 'text': utils.new_uuid()}
        m = TestModel(id=expected['id'], text=expected['text'])
        m.extra = 'this should not be in the dictionary'
        self.assertEqual(m.to_dict(), expected)


class TestMPModel(ModelBase, sql.MaterializedPathMixin):
    """Test docstring"""
    __tablename__ = 'testmpmodel'
    id = sql.Column(sql.String(64), primary_key=True)
    parent_id = sql.Column(sql.String(64), nullable=True)
    text = sql.Column(sql.String(64), nullable=False)


class TestMaterializedPath(tests.TestCase, tests.SQLDriverOverrides):

    def setUp(self):
        super(TestMaterializedPath, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()

        # populate the engine with tables & fixtures
        self.load_fixtures(default_fixtures)
        # defaulted by the data load
        self.user_foo['enabled'] = True

        self.session = sql.get_session()
        self.tree = self._create_branch()

    def config_files(self):
        config_files = super(TestMaterializedPath, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_sql.conf'))
        return config_files

    def _create_node(self):
        return TestMPModel(id=utils.new_uuid(), text=utils.new_uuid())

    def _create_branch(self):
        """Create a branch"""
        a = self._create_node()
        b = self._create_node()
        c = self._create_node()
        b.parent_id = a.id
        c.parent_id = a.id
        return a

    def test_append_branch(self):
        appended = self._create_branch()
        descendants = self.tree.query_descendants(self.session)
        appended.parent_id = descendants[0].id

    def test_move_branch(self):
        """Branch is moved under it's new parent"""

    def test_delete_branch(self):
        """Branch is removed from the tree"""