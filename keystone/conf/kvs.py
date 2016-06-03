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
ALL_OPTS = [
    cfg.ListOpt('backends', default=[],
                help='Extra dogpile.cache backend modules to register '
                     'with the dogpile.cache library.'),
    cfg.StrOpt('config_prefix', default='keystone.kvs',
               help='Prefix for building the configuration dictionary '
                    'for the KVS region. This should not need to be '
                    'changed unless there is another dogpile.cache '
                    'region with the same configuration name.'),
    cfg.BoolOpt('enable_key_mangler', default=True,
                help='Toggle to disable using a key-mangling function '
                     'to ensure fixed length keys. This is toggle-able '
                     'for debugging purposes, it is highly recommended '
                     'to always leave this set to true.'),
    cfg.IntOpt('default_lock_timeout', default=5,
               help='Default lock timeout (in seconds) for distributed '
                    'locking.'),
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
