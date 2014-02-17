# Copyright 2012 SINA Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""Generates a man page for a command-line utility."""

from __future__ import print_function

import argparse
import imp
import os
import sys

from oslo.config import cfg
import stevedore.named

from keystone.openstack.common import gettextutils
from keystone.openstack.common import importutils

gettextutils.install('keystone')


PY_EXT = ".py"


def generate(argv):
    parser = argparse.ArgumentParser(
        description='generate sample configuration file',
    )

    parser.add_argument('-m', dest='modules', action='append')
    parser.add_argument('-l', dest='libraries', action='append')
    parser.add_argument('srcfiles', nargs='*')
    parsed_args = parser.parse_args(argv)

    mods_by_pkg = dict()
    for filepath in parsed_args.srcfiles:
        pkg_name = filepath.split(os.sep)[1]
        mod_str = '.'.join(['.'.join(filepath.split(os.sep)[:-1]),
                            os.path.basename(filepath).split('.')[0]])
        mods_by_pkg.setdefault(pkg_name, list()).append(mod_str)
    # NOTE(lzyeval): place top level modules before packages
    pkg_names = sorted(pkg for pkg in mods_by_pkg if pkg.endswith(PY_EXT))
    ext_names = sorted(pkg for pkg in mods_by_pkg if pkg not in pkg_names)
    pkg_names.extend(ext_names)

    # opts_by_group is a mapping of group name to an options list
    # The options list is a list of (module, options) tuples
    opts_by_group = {'DEFAULT': []}

    if parsed_args.modules:
        for module_name in parsed_args.modules:
            module = _import_module(module_name)
            if module:
                for group, opts in _list_opts(module):
                    opts_by_group.setdefault(group, []).append((module_name,
                                                                opts))

    # Look for entry points defined in libraries (or applications) for
    # option discovery, and include their return values in the output.
    #
    # Each entry point should be a function returning an iterable
    # of pairs with the group name (or None for the default group)
    # and the list of Opt instances for that group.
    if parsed_args.libraries:
        loader = stevedore.named.NamedExtensionManager(
            'oslo.config.opts',
            names=list(set(parsed_args.libraries)),
            invoke_on_load=False,
        )
        for ext in loader:
            for group, opts in ext.plugin():
                opt_list = opts_by_group.setdefault(group or 'DEFAULT', [])
                opt_list.append((ext.name, opts))

    for pkg_name in pkg_names:
        mods = mods_by_pkg.get(pkg_name)
        mods.sort()
        for mod_str in mods:
            if mod_str.endswith('.__init__'):
                mod_str = mod_str[:mod_str.rfind(".")]

            mod_obj = _import_module(mod_str)
            if not mod_obj:
                raise RuntimeError("Unable to import module %s" % mod_str)

            for group, opts in _list_opts(mod_obj):
                opts_by_group.setdefault(group, []).append((mod_str, opts))

    CONF = cfg.CONF

    project = 'keystone'
    prog = 'keystone-all'
    version = None
    usage = None
    default_config_files = None

    CONF._pre_setup(project, prog, version, usage, default_config_files)
    CONF._setup(project, prog, version, usage, default_config_files)

    for opt, group in sorted(CONF._all_cli_opts(),
                             key=lambda x: x[0].name):
        opt._add_to_cli(CONF._oparser, group)

    CONF._oparser.initialize_parser_arguments()

    help_ = CONF._oparser.format_help()

    print('help:\n\n%s\n\n' % help_)

    help_lines = help_.split('\n')

    split_at = help_lines.index('optional arguments:')

    usage_lines = help_lines[0:split_at - 1]
    usage_lines[0] = '  ' + usage_lines[0][7:]
    usage = '\n'.join(usage_lines)

    options_lines = help_lines[split_at + 1:-1]
    options = '\n'.join(options_lines)

    tpl_fn = '/opt/stack/keystone/keystone/tools/template/keystone-all.rst'

    with open(tpl_fn, 'r') as f:
        tpl = f.read()

    out_file = '/opt/stack/keystone/doc/source/man/keystone-all-g.rst'

    def _rst_ize(s):
        return s.replace('*', '\*')

    with open(out_file, 'w+') as f:
        f.write(tpl.format(usage=_rst_ize(usage), options=_rst_ize(options)))


def _import_module(mod_str):
    try:
        if mod_str.startswith('bin.'):
            imp.load_source(mod_str[4:], os.path.join('bin', mod_str[4:]))
            return sys.modules[mod_str[4:]]
        else:
            return importutils.import_module(mod_str)
    except Exception as e:
        sys.stderr.write("Error importing module %s: %s\n" % (mod_str, str(e)))
        return None


def _is_in_group(opt, group):
    "Check if opt is in group."
    for value in group._opts.values():
        # NOTE(llu): Temporary workaround for bug #1262148, wait until
        # newly released oslo.config support '==' operator.
        if not(value['opt'] != opt):
            return True
    return False


def _guess_groups(opt, mod_obj):
    # is it in the DEFAULT group?
    if _is_in_group(opt, cfg.CONF):
        return 'DEFAULT'

    # what other groups is it in?
    for value in cfg.CONF.values():
        if isinstance(value, cfg.CONF.GroupAttr):
            if _is_in_group(opt, value._group):
                return value._group.name

    raise RuntimeError(
        "Unable to find group for option %s, "
        "maybe it's defined twice in the same group?"
        % opt.name
    )


def _list_opts(obj):
    def is_opt(o):
        return (isinstance(o, cfg.Opt) and
                not isinstance(o, cfg.SubCommandOpt))

    opts = list()
    for attr_str in dir(obj):
        attr_obj = getattr(obj, attr_str)
        if is_opt(attr_obj):
            opts.append(attr_obj)
        elif (isinstance(attr_obj, list) and
              all(map(lambda x: is_opt(x), attr_obj))):
            opts.extend(attr_obj)

    ret = {}
    for opt in opts:
        ret.setdefault(_guess_groups(opt, obj), []).append(opt)
    return ret.items()


def main():
    generate(sys.argv[1:])

if __name__ == '__main__':
    main()
