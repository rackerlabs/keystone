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
from keystone.tests import unit
from keystone.tests.unit.ksfixtures import database
from keystone.tests.unit import utils


ModelBase = declarative.declarative_base()


class TestModel(ModelBase, sql.ModelDictMixin):
    __tablename__ = 'testmodel'
    id = sql.Column(sql.String(64), primary_key=True)
    text = sql.Column(sql.String(64), nullable=False)


class TestModelDictMixin(unit.BaseTestCase):

    def test_creating_a_model_instance_from_a_dict(self):
        d = {'id': utils.new_uuid(), 'text': utils.new_uuid()}
        m = TestModel.from_dict(d)
        self.assertEqual(d['id'], m.id)
        self.assertEqual(d['text'], m.text)

    def test_creating_a_dict_from_a_model_instance(self):
        m = TestModel(id=utils.new_uuid(), text=utils.new_uuid())
        d = m.to_dict()
        self.assertEqual(d['id'], m.id)
        self.assertEqual(d['text'], m.text)

    def test_creating_a_model_instance_from_an_invalid_dict(self):
        d = {'id': utils.new_uuid(), 'text': utils.new_uuid(), 'extra': None}
        self.assertRaises(TypeError, TestModel.from_dict, d)

    def test_creating_a_dict_from_a_model_instance_that_has_extra_attrs(self):
        expected = {'id': utils.new_uuid(), 'text': utils.new_uuid()}
        m = TestModel(id=expected['id'], text=expected['text'])
        m.extra = 'this should not be in the dictionary'
        self.assertEqual(expected, m.to_dict())


class ExampleWithPathColumn(ModelBase):

    __tablename__ = 'examplewithpathcolumn'

    id = sql.Column(sql.String(64), primary_key=True, unique=True)
    path1 = sql.Column(sql.MaterializedPathType(), default=[])


class TestMaterializedPathColumn(unit.SQLDriverOverrides, unit.TestCase):

    # Initialization

    def setUp(self):
        super(TestMaterializedPathColumn, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()

        ExampleWithPathColumn.__table__.create(sql.get_engine())

    def config_files(self):
        config_files = super(TestMaterializedPathColumn, self).config_files()
        config_files.append(unit.dirs.tests_conf('backend_sql.conf'))
        return config_files

    # Tests

    @staticmethod
    def _create_node():
        """Test node creation shortcut"""
        node = ExampleWithPathColumn(id=utils.new_uuid())
        return node

    def test_create_node(self):
        """Created node has empty path"""
        node = self._create_node()
        self.assertFalse(node.path1)

    def test_path_column_stores_array(self):
        """Stored and returned value has type list"""
        node = self._create_node()
        example = [utils.new_uuid(), utils.new_uuid()]

        session = sql.get_session()
        session.add(node)
        with session.begin():
            node.path1 = example

        instance = session.query(ExampleWithPathColumn).one()
        self.assertIsInstance(instance.path1, list)
