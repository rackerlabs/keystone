"""OpenStack Identity (Keystone) Management"""


import argparse
import pkgutil
import os
import sys

from keystone.manage2 import commands


# builds a complete path to the commands package
PACKAGE_PATH = os.path.dirname(commands.__file__)

# builds a list of modules in the commands package
MODULES = [tupl for tupl in pkgutil.iter_modules([PACKAGE_PATH])]


def load_module(module_name):
    """Effectively imports a module given the module name"""
    # TODO(dolph): there's probably a way to do this without a loop
    for module_loader, name, is_package in MODULES:
        if name == module_name:
            loader = module_loader.find_module(name)
            module = loader.load_module(name)
            return module

    # this should never be reached, because
    # we already verified the module exists
    assert False


def main():
    # discover command modules
    module_names = [name for _, name, _ in MODULES]
    module_names.sort()

    # we need the name of the command before hitting argparse
    command = None
    i = 0
    for arg in sys.argv:
        if arg in module_names:
            command = sys.argv.pop(i)
            break
        i += 1

    if command and command in module_names:
        # load, configure and run command
        module = load_module(command)
        parser = argparse.ArgumentParser(prog=command,
            description=module.Command.__doc__)

        # let the command append arguments to the parser
        module.Command.append_parser(parser)
        args = parser.parse_args()

        # command
        exit(module.Command.run(args))
    else:
        # show help
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('command', metavar='command', type=str,
            help=', '.join(module_names))
        args = parser.parse_args()

        parser.print_help()

        # always exit 2; something about the input args was invalid
        exit(2)
