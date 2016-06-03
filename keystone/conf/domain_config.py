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


GROUP_NAME = __name__.split('.')[-1]

driver = cfg.StrOpt(
    'driver',
    default='sql',
    help="""
Entrypoint for the domain config backend driver in the
keystone.resource.domain_config namespace.
""")

caching = cfg.BoolOpt(
    'caching',
    default=True,
    help="""
Toggle for domain config caching. This has no effect unless global caching is
enabled.
""")

cache_time = cfg.IntOpt(
    'cache_time',
    default=300,
    help="""
TTL (in seconds) to cache domain config data. This has no effect unless domain
config caching is enabled.
""")


ALL_OPTS = [
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
