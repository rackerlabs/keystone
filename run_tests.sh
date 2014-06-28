#!/bin/bash

# Copyright 2012 OpenStack Foundation
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

set -eu

function usage {
    echo "Usage: $0 [OPTION]..."
    echo "Run Keystone's test suite(s)"
    echo ""
    echo "      --python26           Run Python 2.6 Unit Tests"
    echo "      --python27           Run Python 2.7 Unit Tests"
    echo "      --python33           Run Python 3.3 Unit Tests"
    echo "  -a, --all-python-vers    Run unit tests for all python versions (same as --python26 --python27 --python33)"
    echo "  -x, --failfast           Stop running tests after the first error or failure."
    echo "  -r, --recreate           Force re-creatation of virtual environments. Useful when dependencies have been added."
    echo "  -p, --pep8               Just run flake8 (No unit tests will be run)"
    echo "  -P, --no-pep8            Don't run flake8"
    echo "  -c, --coverage           Generate coverage report"
    echo "  -d, --docs               Generate documentations"
    echo "  -s, --sample-config      Generate a new sample configuration"
    echo "  -h, --help               Print this usage message"
    echo ""
    echo "Note: with no options specified, the script will try to run the python 2.7 tests and pep8."
    echo "      Tox will create a virtual environment for running tests, the first run may take a long"
    echo "      time due to the installation of all the requirements and test-requirements."
    echo ""
    echo "Note: This script requires tox 1.6.x to be installed and python-subunit."
    exit
}

declare -a ENVS=()
declare -a NONSUBUNIT_ENVS=()

function process_option {
    case "$1" in
        --python26) ENVS=( ${ENVS[@]:-} "py26" ) ;;
        --python27) ENVS=( ${ENVS[@]:-} "py27" ) ;;
        --python33) ENVS=( ${ENVS[@]:-} "py33" ) ;;
        -a|--all-python-vers) all_python=1;;
        -x|--failfast) failfast=1;;
        -r|--recreate) recreate="-r";;
        -p|--pep8) just_flake8=1;;
        -P|--no-pep8) no_flake8=1;;
        -c|--coverage) ENVS=( ${ENVS[@]:-} "cover") ;;
        -d|--docs) NONSUBUNIT_ENVS=( ${NONSUBUNIT_ENVS[@]:-} "docs" ) ;;
        -s|--sample-config) NONSUBUNIT_ENVS=( ${NONSUBUNIT_ENVS[@]:-} "sample_config" ) ;;
        -h|--help) usage;;
        -*) testropts="$testropts $1";;
        *) testrargs="$testrargs $1"
    esac
}


all_python=0
failfast=0
recreate=
just_flake8=0
no_flake8=0
testrargs=
testropts="--subunit"

for arg in "$@"; do
    process_option $arg
done

function join {
    local IFS="$1";
    shift; echo "$*";
}

function exists {
    if [[ $(command -v $1 >/dev/null 2>&1) ]]; then
        echo "Command $1 is required, but could not be found."
        exit
    fi
}

function run_tests {
    set -e

    exists tox
    exists subunit-2to1

    if [[ "$just_flake8" -eq "1" ]]; then
        NONSUBUNIT_ENVS=( "pep8" "bash8")
        ENVS=()
    else
        if [[ "$all_python" -eq "1" ]]; then
            ENVS=( ${ENVS[@]/py*/} )
            ENVS=( ${ENVS[@]:-} "py26" "py27" "py33" )
        fi
        if [[ "${#ENVS[@]}" -eq "0" ]]; then
            ENVS=( "py27" )
        fi
        if [[ "$no_flake8" -eq "0" ]]; then
            NONSUBUNIT_ENVS=( "pep8" "bash8" ${NONSUBUNIT_ENVS[@]} )
        fi
        if [[ "$failfast" -eq "1" ]]; then
            testropts="$testropts -- --failfast"
        fi
    fi

    if [[ ! -z $testropts ]]; then
        testropts="-- $testropts"
    fi
    if [[ ${#NONSUBUNIT_ENVS[@]} -ne 0 ]]; then
        local nonsubunit_envs_list=$( join , "${NONSUBUNIT_ENVS[@]:-}" )
        echo "Running: tox -e${nonsubunit_envs_list} ${recreate}"
        tox -e${nonsubunit_envs_list}
    fi
    if [[ ${#ENVS[@]} -ne 0 ]]; then
        local envs_list=$( join , "${ENVS[@]:-}" )
        echo "Running: tox -e${envs_list} ${recreate} ${testrargs} ${testropts} | subunit-2to1 | tools/colorizer.py"
        tox -e${envs_list} ${recreate} ${testrargs} ${testropts} | subunit-2to1 | tools/colorizer.py
    fi
}

run_tests
