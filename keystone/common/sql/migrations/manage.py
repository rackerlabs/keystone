#!/usr/bin/env python3
# Copyright 2012 OpenStack Foundation
#
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

import copy
import os

from alembic import command as alembic_command
from alembic import util as alembic_util
from oslo_config import cfg
from oslo_log import log
from oslo_utils import fileutils
import pbr.version

from keystone.common import sql
from keystone.common.sql import upgrades
import keystone.conf
from keystone.i18n import _

CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


def _get_version_branch_path(release=None, branch=None):
    version_path = upgrades.VERSIONS_PATH
    if branch and release:
        return os.path.join(version_path, release, branch)
    return version_path


def _check_bootstrap_new_branch(branch, version_path, addn_kwargs):
    addn_kwargs['version_path'] = version_path
    addn_kwargs['head'] = f'{branch}@head'
    if not os.path.exists(version_path):
        # Bootstrap initial directory structure
        fileutils.ensure_tree(version_path, mode=0o755)


def do_alembic_command(config, cmd, revision=None, **kwargs):
    args = []
    if revision:
        args.append(revision)

    try:
        getattr(alembic_command, cmd)(config, *args, **kwargs)
    except alembic_util.CommandError as e:
        alembic_util.err(str(e))


def do_generic_show(config, cmd):
    kwargs = {'verbose': CONF.command.verbose}
    do_alembic_command(config, cmd, **kwargs)


def do_validate(config, cmd):
    do_alembic_command(config, 'branches')
    # TODO(stephenfin): Implement these
    # validate_revisions(config)
    # TODO(stephenfin): Implement these
    # validate_head_files(config)


def do_revision(config, cmd):
    kwargs = {
        'message': CONF.command.message,
        'autogenerate': CONF.command.autogenerate,
        'sql': CONF.command.sql,
    }
    branches = []
    if CONF.command.expand:
        kwargs['head'] = 'expand@head'
        branches.append(upgrades.EXPAND_BRANCH)
    elif CONF.command.contract:
        kwargs['head'] = 'contract@head'
        branches.append(upgrades.CONTRACT_BRANCH)
    else:
        branches = upgrades.MIGRATION_BRANCHES

    if not CONF.command.autogenerate:
        for branch in branches:
            args = copy.copy(kwargs)
            version_path = _get_version_branch_path(
                release=upgrades.CURRENT_RELEASE,
                branch=branch,
            )
            _check_bootstrap_new_branch(branch, version_path, args)
            do_alembic_command(config, cmd, **args)
    else:
        # autogeneration code will take care of enforcing proper directories
        do_alembic_command(config, cmd, **kwargs)

    # TODO(stephenfin): Implement these
    # update_head_files(config)


def add_branch_options(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--expand', action='store_true')
    group.add_argument('--contract', action='store_true')
    return group


def add_alembic_subparser(sub, cmd):
    return sub.add_parser(cmd, help=getattr(alembic_command, cmd).__doc__)


def add_command_parsers(subparsers):
    for name in ['current', 'history', 'branches', 'heads']:
        parser = add_alembic_subparser(subparsers, name)
        parser.set_defaults(func=do_generic_show)
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Display more verbose output for the specified command',
        )

    parser = subparsers.add_parser(
        'validate',
        help=alembic_command.branches.__doc__ + ' and validate head file',
    )
    parser.set_defaults(func=do_validate)

    parser = add_alembic_subparser(subparsers, 'revision')
    parser.add_argument('-m', '--message')
    parser.add_argument('--sql', action='store_true')
    group = add_branch_options(parser)
    group.add_argument('--autogenerate', action='store_true')
    parser.set_defaults(func=do_revision)


command_opt = cfg.SubCommandOpt(
    'command',
    title='Command',
    help=_('Available commands'),
    handler=add_command_parsers,
)


def main():
    CONF.register_cli_opt(command_opt)

    keystone.conf.configure()
    sql.initialize()

    CONF(
        project='keystone',
        version=pbr.version.VersionInfo('keystone').version_string(),
    )
    config = upgrades.get_alembic_config()

    return bool(CONF.command.func(config, CONF.command.name))


if __name__ == '__main__':
    main()
