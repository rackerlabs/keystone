# Copyright 2019 SUSE LLC
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

from keystone.common import resource_options
from keystone.common.validation import parameter_types


ROLE_OPTIONS_REGISTRY = resource_options.ResourceOptionRegistry('ROLE')
IMMUTABLE_OPT = (
    resource_options.ResourceOption(
        option_id='1000',
        option_name='immutable',
        validator=resource_options.boolean_validator,
        json_schema_validation=parameter_types.boolean))


def register_role_options():
    for opt in [
        IMMUTABLE_OPT,
    ]:
        ROLE_OPTIONS_REGISTRY.register_option(opt)


register_role_options()
