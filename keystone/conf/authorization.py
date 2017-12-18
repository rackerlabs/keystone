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


enforce_system_scope = cfg.BoolOpt(
    'enforce_system_scope',
    default=False,
    help=utils.fmt("""
This option controls whether or not to enforce scope when calling keystone APIs
or accessing keystone policies. The Queens release included a new type of scope
called ``system`` scope that allows users have role assignments on the
deployment system in addition to projects and domains. To allow for backwards
compatibility, a user may need to access system-level APIs with a
project-scoped token. Once actual system users have been granted roles on the
system, this should be flipped to ``True``, which will require requests to be
made with scope necessary for the operation. Do not set this option to ``True``
without having at least one administrator role assignment on the system.
Without at least one administrator system role assignment, the deployments
system-level keystone APIs will be locked for everyone.
"""))

GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [enforce_system_scope]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
