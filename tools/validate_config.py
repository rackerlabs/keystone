# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from oslo_config import cfg
from oslo_config import generator
from oslo_config import validator
import logging


_NAMESPACE_HINTS = '../config-generator/keystone.conf'
_IGNORE = ['os_inherit']


def _parse_namespaces(file_path):
    config = cfg.ConfigParser(file_path, {})
    config.parse()
    return config.sections['DEFAULT']['namespace']


def main(args=None):
    namespaces = _parse_namespaces(_NAMESPACE_HINTS)
    real_conf_path = cfg.find_config_files('keystone')[0]
    results = validator.validate(real_conf_path,
                                 generator._list_opts(namespaces),
                                 _IGNORE)
    validator.report(results)


if __name__ == '__main__':
    main()
