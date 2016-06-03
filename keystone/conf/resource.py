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
    cfg.StrOpt('driver',
               help='Entrypoint for the resource backend driver in the '
                    'keystone.resource namespace. Only an SQL driver is '
                    'supplied. If a resource driver is not specified, '
                    'the assignment driver will choose the resource '
                    'driver.'),
    cfg.BoolOpt('caching', default=True,
                deprecated_opts=[cfg.DeprecatedOpt('caching',
                                                   group='assignment')],
                help='Toggle for resource caching. This has no effect '
                     'unless global caching is enabled.'),
    cfg.IntOpt('cache_time',
               deprecated_opts=[cfg.DeprecatedOpt('cache_time',
                                                  group='assignment')],
               help='TTL (in seconds) to cache resource data. This has '
                    'no effect unless global caching is enabled.'),
    cfg.IntOpt('list_limit',
               deprecated_opts=[cfg.DeprecatedOpt('list_limit',
                                                  group='assignment')],
               help='Maximum number of entities that will be returned '
                    'in a resource collection.'),
    cfg.StrOpt('admin_project_domain_name',
               help='Name of the domain that owns the '
                    '`admin_project_name`. Defaults to None.'),
    cfg.StrOpt('admin_project_name',
               help='Special project for performing administrative '
               'operations on remote services. Tokens scoped to '
               'this project will contain the key/value '
               '`is_admin_project=true`. Defaults to None.'),
    cfg.StrOpt('project_name_url_safe',
               choices=['off', 'new', 'strict'], default='off',
               help='Whether the names of projects are restricted from '
                    'containing url reserved characters. If set to new, '
                    'attempts to create or update a project with a url '
                    'unsafe name will return an error. In addition, if '
                    'set to strict, attempts to scope a token using '
                    'an unsafe project name will return an error.'),
    cfg.StrOpt('domain_name_url_safe',
               choices=['off', 'new', 'strict'], default='off',
               help='Whether the names of domains are restricted from '
                    'containing url reserved characters. If set to new, '
                    'attempts to create or update a domain with a url '
                    'unsafe name will return an error. In addition, if '
                    'set to strict, attempts to scope a token using a '
                    'domain name which is unsafe will return an error.'),
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
