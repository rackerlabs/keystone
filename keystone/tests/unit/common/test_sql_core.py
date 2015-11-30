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

import six
from sqlalchemy.ext import declarative

from oslo_db import exception as db_exception

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
    path2 = sql.Column(sql.MaterializedPathType(), default=[])


class TestMaterializedPathColumn(unit.SQLDriverOverrides, unit.TestCase):

    # Initialization

    def setUp(self):
        super(TestMaterializedPathColumn, self).setUp()
        self.useFixture(database.Database())

        ExampleWithPathColumn.__table__.create(sql.get_engine())

        self.session = sql.get_session()

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

    def test_path_column_stores_array_as_string_and_returns_array(self):
        """Value is represented as list, stored as string"""
        node = self._create_node()
        example = [utils.new_uuid(), utils.new_uuid()]

        self.session.add(node)
        with self.session.begin():
            node.path1 = example

        rows = self.session.connection().execute(
            sql.sql.text("select id, path1 from examplewithpathcolumn")
        )
        self.assertIsInstance(list(rows)[0]['path1'], six.text_type)

        instance = self.session.query(ExampleWithPathColumn).one()
        self.assertIsInstance(instance.path1, list)

    def test_multiple_paths_independent(self):
        """Manipulation with one path don't change another"""
        node = self._create_node()
        example1 = [utils.new_uuid(), utils.new_uuid()]
        example2 = [utils.new_uuid(), utils.new_uuid()]

        self.session.add(node)
        with self.session.begin():
            node.path1 = example1
            node.path2 = example2

        instance = self.session.query(ExampleWithPathColumn).one()
        self.assertEqual(example2, instance.path2)

        with self.session.begin():
            node.path1 = node.path1 + [utils.new_uuid()]

        instance = self.session.query(ExampleWithPathColumn).one()
        self.assertNotEqual(example1, instance.path1)
        self.assertEqual(example2, instance.path2)

    def test_delimiter_in_path(self):
        """Delimiter in stored path results in error

        DBError is raised upon attempt to store path with an element,
        containing path delimiter.
        """
        node = self._create_node()
        example1 = [utils.new_uuid(),
                    utils.new_uuid() + sql.MaterializedPathType.DELIMITER]

        self.session.add(node)
        self.session.begin()
        node.path1 = example1
        self.assertRaises(db_exception.DBError, self.session.commit)
