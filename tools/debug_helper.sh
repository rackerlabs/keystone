#!/bin/bash

ALL_TESTS=`mktemp ks_all.XXXXXXXXXX` || exit 1
TESTS_TO_RUN=`mktemp ks_to_run.XXXXXXXXXX` || exit 1

python -m testtools.run discover -t ./ ./keystone/tests --list > $ALL_TESTS

if [ "$1" ]
then
    grep "$1" < $ALL_TESTS > $TESTS_TO_RUN
else
    mv $ALL_TESTS $TESTS_TO_RUN
fi

python -m testtools.run discover --load-list $TESTS_TO_RUN
