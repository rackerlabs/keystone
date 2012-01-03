import argparse
import prettytable

from keystone import backends
from keystone.managers.token import Manager as TokenManager
from keystone.managers.tenant import Manager as TenantManager
from keystone.managers.user import Manager as UserManager
from keystone.managers.role import Manager as RoleManager
from keystone.managers.grant import Manager as GrantManager
from keystone.managers.service import Manager as ServiceManager


def arg(name, **kwargs):
    """Decorate the command class with an argparse argument"""
    def _decorator(cls):
        if not hasattr(cls, '_args'):
            setattr(cls, '_args', {})
        args = getattr(cls, '_args')
        args[name] = kwargs
        return cls
    return _decorator


class BaseCommand(object):
    """Provides a common pattern for keystone-manage commands"""

    def __init__(self, *args, **kwargs):
        if not hasattr(self.__class__, '_args'):
            setattr(self.__class__, '_args', {})

    def build_parser(self):
        """Returns an argparser for the command"""
        parser = argparse.ArgumentParser()
        self.append_parser(parser)
        return parser

    # pylint: disable=E1101
    def append_parser(self, parser):
        """Appends this command's arguments to an argparser

        :param parser: argparse.ArgumentParser
        """
        args = self.__class__._args

        for name in args.keys():
            try:
                parser.add_argument(name, **args[name])
            except TypeError:
                print "Unable to add argument (%s) %s" % (name, args[name])
                raise

    def run(self, args):
        """Handles argparse args and prints command results to stdout

        :param args: argparse Namespace
        """
        raise NotImplementedError()


class BaseBackendCommand(BaseCommand):
    """Common functionality for commands requiring backend access"""

    def __init__(self, managers, *args, **kwargs):
        super(BaseBackendCommand, self).__init__(*args, **kwargs)

        # injected managers become available as self.attributes
        for name, manager in managers.iteritems():
            setattr(self, name, manager)

    @staticmethod
    def _get(obj_name, manager, id=None):
        """Get an object from a manager, or fail if not found"""
        if id is not None:
            obj = manager.get(id)

            if obj is None:
                raise KeyError("%s ID not found: %s" % (obj_name, id))

        return obj

    # pylint: disable=E1101
    def get_user(self, id):
        return BaseBackendCommand._get("User", self.user_manager, id)

    # pylint: disable=E1101
    def get_tenant(self, id):
        return BaseBackendCommand._get("Tenant", self.tenant_manager, id)


class ListMixin(object):
    """Implements common patterns for list_* commands"""

    @staticmethod
    def build_table(columns):
        table = prettytable.PrettyTable(columns)

        # set default alignment
        for column in columns:
            table.set_field_align(column, "l")

        return table

    @staticmethod
    def print_table(table):
        table.printt(sortby="Name")


def init_managers(options):
    """Initializes backend storage and return managers"""
    backends.configure_backends(options)

    managers = {}
    managers['token_manager'] = TokenManager(options)
    managers['tenant_manager'] = TenantManager(options)
    managers['user_manager'] = UserManager(options)
    managers['role_manager'] = RoleManager(options)
    managers['grant_manager'] = GrantManager(options)
    managers['service_manager'] = ServiceManager(options)
    return managers
