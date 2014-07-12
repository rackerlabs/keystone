# Copyright 2014 IBM Corp.
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

from keystone.common import controller
from keystone import config

CONF = config.CONF


class RestConfigV3Controller(controller.V3Controller):

    def _read_config_options(self, group):

        def _sanitize(opt, value):
            """Obfuscate values of options declared secret."""
            return value if not opt.secret else '*' * len(str(value))

        def _read_group(config_dict, name):
            group_attr = CONF.GroupAttr(CONF, CONF._get_group(name))
            d[name] = {}
            for opt_name in sorted(CONF._groups[name]._opts):
                opt = CONF._get_opt_info(opt_name, name)['opt']
                d[name][opt_name] = _sanitize(opt, getattr(group_attr,
                                                           opt_name))

        d = {}
        if group is not None:
            if group in CONF._groups:
                _read_group(d, group)
            return d

        for opt_name in sorted(CONF._opts):
            opt = CONF._get_opt_info(opt_name)['opt']
            d[opt_name] = _sanitize(opt, getattr(CONF, opt_name))

        for group_name in CONF._groups:
            _read_group(d, group_name)

        return d

    @controller.protected()
    def get_config(self, context):
        ref = self._read_config_options(
            context['query_string'].get('group', None))
        return {'config': ref}
