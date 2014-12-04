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

HERE=$(cd $(dirname "$0") && pwd)

trap "cleanup" EXIT

function cleanup {
    echo 'cleaning'
    # TODO(dstanek): the pre-test hook adds files into devstack
    # this hook should clean them out
}

function pre_test_hook {
    # TODO(dstanek): maybe we should save off any existing local.conf?
    cp $HERE/devstack/local.conf $DEVSTACK_BASE
    $HERE/devstack-gate/pre_test_hook.sh
}

function post_test_hook {
    $HERE/devstack-gate/post_test_hook.sh
}

function run_tests {
    echo run tests
    # TODO(dstanek): add the actual test run step
     tox -e functional_federation
}

function stack {
    $DEVSTACK_BASE/stack.sh
}

function unstack {
    $DEVSTACK_BASE/unstack.sh
}

export DEVSTACK_BASE=${DEVSTACK_GATE:-$HOME/devstack}

pre_test_hook
stack
run_tests
unstack
post_test_hook
