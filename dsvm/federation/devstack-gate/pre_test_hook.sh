#!/bin/bash

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

# Run by devstack-gate

HERE=$(cd $(dirname "$0") && pwd)
DEVSTACK_BASE=${DEVSTACK_BASE:-$BASE/new/devstack}

cp $HERE/../devstack/extras.d/* $DEVSTACK_BASE/extras.d/
cp $HERE/../devstack/files/* $DEVSTACK_BASE/files/
cp $HERE/../devstack/lib/* $DEVSTACK_BASE/lib/
