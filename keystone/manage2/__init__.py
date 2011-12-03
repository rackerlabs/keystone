"""OpenStack Identity (Keystone) Management CLI"""


import argparse
import logging
import pkgutil
import os
import sys

from keystone.manage2 import commands


LOGGER = logging.getLogger(__name__)
PACKAGE_PATH = os.path.dirname(commands.__file__)
MODULES = [tupl for tupl in pkgutil.iter_modules([PACKAGE_PATH])]


def load_module(module_name):
    LOGGER.info('loading module %s' % module_name)

    # TODO(dolph): there's probably a way to do this without a loop
    for module_loader, name, is_package in MODULES:
        if name == module_name:
            loader = module_loader.find_module(name)
            module = loader.load_module(name)
            return module

    # this should never be reached, because
    # we already verified the module exists
    assert False


def append_parser(module, parser):
    cmd = module.Command
    cmd.append_parser(parser)


def main():
    logging.basicConfig(format='%(levelname)s: %(message)s')

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

    parser = argparse.ArgumentParser(prog=command, description=__doc__)

    if command and command in module_names:
        module = load_module(command)

        # dynamically configure and re-run parser
        append_parser(module, parser)
        args = parser.parse_args()

        exit(module.Command.run(args))
    else:
        # show help
        parser.add_argument('command', metavar='command', type=str,
            help=', '.join(module_names))
        args = parser.parse_args()

        parser.print_help()
        exit(2)
