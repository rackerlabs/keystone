#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import os

from oslo.config import cfg
from oslo.config import generator


def generate_config(_cfg):
    conf = cfg.CONF
    # TODO(morganfainberg): update oslo.config to allow setting up generator
    # options without needing to access a private variable.
    conf.register_opts(generator._generator_opts)
    conf.set_override(name='namespace',
                      override=['keystone', 'oslo.messaging', 'oslo.db'])

    output_file = os.path.normpath(os.path.join(os.path.abspath(__file__),
                                   os.pardir,
                                   os.pardir,
                                   'etc',
                                   'keystone.conf.sample'))

    conf.set_override(name='output_file', override=output_file)

    generator.generate(conf)
