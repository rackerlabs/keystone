import logging
import unittest2 as unittest
import uuid

from keystone.manage2 import common
from keystone.manage2.commands import version
from keystone.manage2.commands import list_users
from keystone.manage2.commands import create_user
from keystone.manage2.commands import update_user
from keystone.manage2.commands import delete_user
from keystone.manage2.commands import list_tenants
from keystone.manage2.commands import create_tenant
from keystone.manage2.commands import update_tenant
from keystone.manage2.commands import delete_tenant
from keystone.tools import buffout


LOGGER = logging.getLogger(__name__)


OPTIONS = {
    "keystone-service-admin-role": "KeystoneServiceAdmin",
    "keystone-admin-role": "KeystoneAdmin",
    "hash-password": "False",
    'backends': 'keystone.backends.sqlalchemy',
    'keystone.backends.sqlalchemy': {
        "sql_connection": "sqlite://",
        "backend_entities": ("['UserRoleAssociation', "
            "'Endpoints', 'Role', 'Tenant', 'User', "
            "'Credentials', 'EndpointTemplates', 'Token', "
            "'Service']"),
        "sql_idle_timeout": "30"}}


class CommandTestCase(unittest.TestCase):
    """Buffers stdout to test keystone-manage commands"""

    def run_cmd(self, module, args=None):
        """Runs the Command in the given module using the provided args"""
        args = args if args is not None else []

        cmd = module.Command(self.managers)
        cmd_parser = cmd.build_parser()
        parsed_args = cmd_parser.parse_args(args)
        cmd.run(parsed_args)

    def setUp(self):
        self.managers = common.init_managers(OPTIONS)

        # buffer stdout so we can assert what's printed
        self.ob = buffout.OutputBuffer()
        self.ob.start()

    def tearDown(self):
        self.ob.stop()


class TestVersionCommand(CommandTestCase):
    """Tests for ./bin/keystone-manage version"""
    API_VERSION = '2.0 beta'
    IMPLEMENTATION_VERSION = '2012.1-dev'

    def test_api_version(self):
        v = version.Command(OPTIONS).get_api_version()
        self.assertEqual(v, self.API_VERSION)

    def test_implementation_version(self):
        v = version.Command(OPTIONS).get_implementation_version()
        self.assertEqual(v, self.IMPLEMENTATION_VERSION)

    def test_no_args(self):
        self.run_cmd(version, [])
        lines = self.ob.read_lines()
        self.assertEqual(len(lines), 2, lines)
        self.assertIn(self.API_VERSION, lines[0])
        self.assertIn(self.IMPLEMENTATION_VERSION, lines[1])

    def test_api_arg(self):
        self.run_cmd(version, ['--api'])
        lines = self.ob.read_lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(self.API_VERSION, lines[0])

    def test_implementation_arg(self):
        self.run_cmd(version, ['--implementation'])
        lines = self.ob.read_lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(self.IMPLEMENTATION_VERSION, lines[0])


class TestCreateUserCommand(CommandTestCase):
    def test_no_args(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(create_user)

    def test_create_user_min_fields(self):
        name = uuid.uuid4().hex
        password = uuid.uuid4().hex
        self.run_cmd(create_user, [
            '--name', name,
            '--password', password])
        user_id = self.ob.read_lines()[0]
        self.assertEqual(len(user_id), 32)

        self.ob.clear()

        self.run_cmd(list_users)
        output = self.ob.read()
        self.assertIn(user_id, output)
        self.assertIn(name, output)
        self.assertNotIn(password, output)

    def test_create_user_all_fields(self):
        user_id = uuid.uuid4().hex
        name = uuid.uuid4().hex
        password = uuid.uuid4().hex
        email = uuid.uuid4().hex
        self.run_cmd(create_user, [
            '--id', user_id,
            '--name', name,
            '--password', password,
            '--email', email,
            '--disable'])
        output = self.ob.read_lines()
        self.assertEquals(user_id, output[0])

        self.ob.clear()

        self.run_cmd(list_users)
        output = self.ob.read()
        self.assertIn(user_id, output)

        lines = self.ob.read_lines()
        row = [row for row in lines if user_id in row][0]
        row = [col for col in row.split() if col.strip() != '|']
        self.assertEquals(user_id, row[0])
        self.assertEquals(name, row[1])
        self.assertEquals(email, row[2])
        self.assertEquals(str(None), row[3])
        self.assertEquals(str(False), row[4])


class TestListUsersCommand(CommandTestCase):
    def test_no_args(self):
        self.run_cmd(list_users)
        lines = self.ob.read_lines()
        self.assertIn('ID', lines[1])
        self.assertIn('Name', lines[1])
        self.assertIn('Enabled', lines[1])
        self.assertIn('Default Tenant ID', lines[1])


class TestUpdateUserCommand(CommandTestCase):
    def test_no_args(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(update_user)

    def test_invalid_id(self):
        with self.assertRaises(KeyError):
            self.run_cmd(update_user, [
                '--where-id', uuid.uuid4().hex])

    def test_create_update_list(self):
        user_id = uuid.uuid4().hex
        self.run_cmd(create_user, [
            '--id', user_id,
            '--name', uuid.uuid4().hex,
            '--password', uuid.uuid4().hex,
            '--email', uuid.uuid4().hex])

        name = uuid.uuid4().hex
        password = uuid.uuid4().hex
        email = uuid.uuid4().hex
        self.run_cmd(update_user, [
            '--where-id', user_id,
            '--name', name,
            '--password', password,
            '--email', email,
            '--disable'])

        self.ob.clear()

        self.run_cmd(list_users)
        output = self.ob.read()
        self.assertIn(user_id, output)

        lines = self.ob.read_lines()
        row = [row for row in lines if user_id in row][0]
        row = [col for col in row.split() if col.strip() != '|']
        self.assertEquals(user_id, row[0])
        self.assertEquals(name, row[1])
        self.assertEquals(email, row[2])
        self.assertEquals(str(None), row[3])
        self.assertEquals(str(False), row[4])


class TestDeleteUserCommand(CommandTestCase):
    def test_no_args(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(delete_user)

    def test_invalid_id(self):
        with self.assertRaises(KeyError):
            self.run_cmd(delete_user, ['--where-id', uuid.uuid4().hex])

    def test_create_delete_list(self):
        user_id = uuid.uuid4().hex
        self.run_cmd(create_user, [
            '--id', user_id,
            '--name', uuid.uuid4().hex,
            '--password', uuid.uuid4().hex,
            '--email', uuid.uuid4().hex])

        self.run_cmd(delete_user, [
            '--where-id', user_id])

        self.ob.clear()

        self.run_cmd(list_users)
        self.assertNotIn(user_id, self.ob.read())


class TestCreateTenantCommand(CommandTestCase):
    def test_no_args(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(create_tenant)

    def test_create_enabled_tenant(self):
        name = uuid.uuid4().hex
        self.run_cmd(create_tenant, [
            '--name', name])
        tenant_id = self.ob.read_lines()[0]
        self.assertEqual(len(tenant_id), 32)

        self.ob.clear()

        self.run_cmd(list_tenants)
        output = self.ob.read()
        self.assertIn(tenant_id, output)
        self.assertIn(name, output)

    def test_create_disabled_tenant(self):
        name = uuid.uuid4().hex
        self.run_cmd(create_tenant, [
            '--name', name,
            '--disabled'])
        tenant_id = self.ob.read_lines()[0]
        self.assertEqual(len(tenant_id), 32)

        self.ob.clear()

        self.run_cmd(list_tenants)
        output = self.ob.read()
        self.assertIn(tenant_id, output)

        lines = self.ob.read_lines()
        row = [row for row in lines if tenant_id in row][0]
        row = [col for col in row.split() if col.strip() != '|']
        self.assertEquals(tenant_id, row[0])
        self.assertEquals(name, row[1])
        self.assertEquals(str(False), row[2])


class TestListTenantsCommand(CommandTestCase):
    def test_no_args(self):
        self.run_cmd(list_tenants)
        lines = self.ob.read_lines()
        self.assertIn('ID', lines[1])
        self.assertIn('Name', lines[1])
        self.assertIn('Enabled', lines[1])


class TestUpdateTenantCommand(CommandTestCase):
    def test_no_args(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(update_tenant)

    def test_invalid_id(self):
        with self.assertRaises(KeyError):
            self.run_cmd(update_tenant, [
                '--where-id', uuid.uuid4().hex])

    def test_create_update_list(self):
        tenant_id = uuid.uuid4().hex
        self.run_cmd(create_tenant, [
            '--id', tenant_id,
            '--name', uuid.uuid4().hex])

        name = uuid.uuid4().hex
        self.run_cmd(update_tenant, [
            '--where-id', tenant_id,
            '--name', name,
            '--disable'])

        self.ob.clear()

        self.run_cmd(list_tenants)
        output = self.ob.read()
        self.assertIn(tenant_id, output)

        lines = self.ob.read_lines()
        row = [row for row in lines if tenant_id in row][0]
        row = [col for col in row.split() if col.strip() != '|']
        self.assertEquals(tenant_id, row[0])
        self.assertEquals(name, row[1])
        self.assertEquals(str(False), row[2])


class TestDeleteTenantCommand(CommandTestCase):
    def test_no_args(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(delete_tenant)

    def test_invalid_id(self):
        with self.assertRaises(KeyError):
            self.run_cmd(delete_tenant, ['--where-id', uuid.uuid4().hex])

    def test_create_delete_list(self):
        tenant_id = uuid.uuid4().hex
        self.run_cmd(create_tenant, [
            '--id', tenant_id,
            '--name', uuid.uuid4().hex])

        self.run_cmd(delete_tenant, [
            '--where-id', tenant_id])

        self.ob.clear()

        self.run_cmd(list_tenants)
        self.assertNotIn(tenant_id, self.ob.read())
