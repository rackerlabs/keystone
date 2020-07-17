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


remove_dangling_assignments = cfg.StrOpt(
    'remove_dangling_assignments',
    default=False,
    help=utils.fmt("""
When auto-provisioning resources when a federated user authenticates, also
remove any dangling role assignments that are no longer declared in the
idp mapping. This can ensure that users are offboarded from projects that
they should no longer be a member of. Defaults to false.
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    remove_dangling_assignments,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
