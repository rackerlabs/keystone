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

import itertools


def list_rules():
    # TODO(lbragstad): As we start to move policy defaults into code, we need
    # to add new defaults to this generator. This ensures our
    # oslo.policy.Enforcer doens't have any gaps or protected APIs.
    return itertools.chain()
