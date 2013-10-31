#!/bin/bash

python -m testtools.run discover -t ./ ./keystone/tests --list > /tmp/ks_all_tests

if [ "$1" ]
then
	grep "$1" < /tmp/ks_all_tests > /tmp/ks_tests_to_run
else
	mv /tmp/ks_all_tests /tmp/ks_tests_to_run
fi

