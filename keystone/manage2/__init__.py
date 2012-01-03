"""OpenStack Identity (Keystone) Management"""


import optparse
import argparse
import pkgutil
import os
import sys

from keystone import version
from keystone.common import config
from keystone.manage2 import commands
from keystone.manage2 import common


# builds a complete path to the commands package
PACKAGE_PATH = os.path.dirname(commands.__file__)

# builds a list of modules in the commands package
MODULES = [tupl for tupl in pkgutil.iter_modules([PACKAGE_PATH])]


def load_module(module_name):
    """Imports a module given the module name"""
    try:
        module_loader, name, is_package = [md for md in MODULES
                if md[1] == module_name][0]
    except IndexError:
        raise ValueError("No module found named '%s'" % module_name)

    loader = module_loader.find_module(name)
    module = loader.load_module(name)
    return module


def get_options():
    # Initialize a parser for our configuration paramaters
    parser = optparse.OptionParser("usage", version='%%prog %s'
        % version.version())
    config.add_common_options(parser)
    config.add_log_options(parser)

    # Parse command-line and load config
    (options, args) = config.parse_options(parser, [])
    _config_file, conf = config.load_paste_config('admin', options, args)

    config.setup_logging(options, conf)

    return conf.global_conf


def main():
    # discover command modules
    module_names = [name for _, name, _ in MODULES]
    module_names.sort()

    # we need the name of the command before hitting argparse
    command = None
    for pos, arg in enumerate(sys.argv):
        if arg in module_names:
            command = sys.argv.pop(pos)
            break

    if command and command in module_names:
        # load, configure and run command
        module = load_module(command)
        parser = argparse.ArgumentParser(prog=command,
            description=module.Command.__doc__)

        # let the command append arguments to the parser
        options = get_options()
        managers = common.init_managers(options)
        cmd = module.Command(managers=managers)
        cmd.append_parser(parser)
        args = parser.parse_args()

        exit(cmd.run(args))
    else:
        # show help
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('command', metavar='command', type=str,
            help=', '.join(module_names))
        args = parser.parse_args()

        parser.print_help()

        # always exit 2; something about the input args was invalid
        exit(2)
