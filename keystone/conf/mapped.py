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

from oslo_config import cfg

from keystone.conf import utils


auto_create_project_by_name = cfg.BoolOpt(
    'auto_create_project_by_name',
    default=True,
    help=utils.fmt("""
Determines if projects mapped by name should be created
"""))

auto_create_project_by_id = cfg.BoolOpt(
    'auto_create_project_by_id',
    default=False,
    help=utils.fmt("""
Determines if projects mapped by ID should be created
"""))

ignore_uncreated_projects = cfg.BoolOpt(
    'ignore_uncreated_projects',
    default=True,
    help=utils.fmt("""
If set, projects that cannot be mapped (by ID or by name) are simply ignored.
If not-set, then exception is thrown and user is not able to authenticate
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    auto_create_project_by_name,
    auto_create_project_by_id,
    ignore_uncreated_projects
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
