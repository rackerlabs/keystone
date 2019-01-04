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


caching = cfg.BoolOpt(
    'caching',
    default=True,
    help=utils.fmt("""
Toggle for application credential caching. This has no effect unless global
caching is enabled.
"""))

cache_time = cfg.IntOpt(
    'cache_time',
    help=utils.fmt("""
Time to cache application credential data in seconds. This has no effect
unless global caching is enabled.
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    caching,
    cache_time,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
