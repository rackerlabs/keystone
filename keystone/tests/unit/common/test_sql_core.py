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
from keystone import exception
from keystone.tests import unit as tests
from keystone.tests.unit.ksfixtures import database
from keystone.tests.unit import utils


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


class ExampleMPModel(ModelBase, sql.MaterializedPathMixin):
    """Model to test materialized path mix-in"""

    __tablename__ = 'testmpmodel'
    ID_COLUMN = 'test_id'
    PARENT_COLUMN = 'test_parent_id'
    attributes = [ID_COLUMN, PARENT_COLUMN, 'text']

    test_id = sql.Column(sql.String(64), primary_key=True)
    test_parent_id = sql.Column(sql.String(64), nullable=True)
    text = sql.Column(sql.String(64), nullable=False)


class TestMaterializedPath(tests.SQLDriverOverrides, tests.TestCase):

    def setUp(self):
        super(TestMaterializedPath, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()

        ExampleMPModel.__table__.create(sql.get_engine())

        # Creating a tree with attached branch
        self.tree = self._create_branch()
        # Create a branch to attach
        self.attached = self._create_branch()
        session = sql.get_session()
        query = session.query(ExampleMPModel)
        descendants = query.filter(self.tree.descendants_filter)
        # Attach the branch to the first tree leaf
        # NOTE(amakarov): any leaf will go, the first is just the easiest one
        with session.begin():
            self.attached.parent = descendants.first()

    def config_files(self):
        config_files = super(TestMaterializedPath, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_sql.conf'))
        return config_files

    def _create_node(self):
        return ExampleMPModel(test_id=utils.new_uuid(), text=utils.new_uuid())

    def _create_branch(self):
        """Create a branch"""
        session = sql.get_session()
        with session.begin():
            a = self._create_node()
            b = self._create_node()
            c = self._create_node()
            b.parent = a
            c.parent = a
            session.add_all([a, b, c])
        return a

    def test_append_branch(self):
        self.assertEqual(self.tree.test_id, self.attached.parent.path)
        expected_path = ExampleMPModel.DELIMITER.join((
            self.tree.test_id, self.attached.parent.test_id
        ))
        self.assertEqual(expected_path, self.attached.path)

        session = sql.get_session()
        query = session.query(ExampleMPModel)
        leaf = query.filter(self.attached.descendants_filter).first()
        expected_path = ExampleMPModel.DELIMITER.join((
            self.tree.test_id, self.attached.parent.test_id,
            self.attached.test_id
        ))
        self.assertEqual(expected_path, leaf.path)

    def test_cyclic_reference(self):
        """Tree has no cycles"""

        def make_cycle():
            self.tree.parent = self.attached

        self.assertRaises(exception.ValidationError, make_cycle)

    def test_delete_branch(self):
        """Branch is removed from the tree"""
        session = sql.get_session()
        descendants = session.query(ExampleMPModel).filter(
            self.attached.descendants_filter)

        self.attached.delete_tree()

        self.assertEqual(0, descendants.count())

    def test_detach_branch(self):
        """Branch is separated"""
        self.attached.parent = None
        session = sql.get_session()
        query = session.query(ExampleMPModel)
        self.assertEqual(
            2, query.filter(self.attached.descendants_filter).count())
