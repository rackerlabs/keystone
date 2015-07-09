#!/usr/bin/env python

# Copyright 2013 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import sys
from oslo_config.cfg import ConfigFilesNotFoundError
# If ../../keystone/__init__.py exists, add ../../ to Python search path, so
# that it will override what happens to be installed in
# /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir,
                                   os.pardir,
                                   os.pardir))
if os.path.exists(os.path.join(possible_topdir,
                               'keystone',
                               '__init__.py')):
    sys.path.insert(0, possible_topdir)

from keystone import cli
from keystone.common import environment


# entry point.
def main():

    dev_conf = os.path.join(possible_topdir,
                            'etc',
                            'keystone.conf')

    environment.use_stdlib()

    def input_parser(usr_response):
        if (usr_response and usr_response[0].lower() == 'a'):
            print ("Aborting...")
        elif (usr_response[0].lower() == "c"):
            print ("Continuing...")
            cli.main(argv=sys.argv, config_files=config_files)
        else:
            print ("Response not recognized. Aborting...")

    def rw_fail_handler():
        usr_response = raw_input("Warning: Could not find keystone.conf in " +
                                 str(config_files) +
                                 " or current user does not have "
                                 "sufficient privileges to access file.\n"
                                 "(a)bort (c)ontinue anyways: ")
        return usr_response

    environment.use_stdlib()

    config_files = None

    if os.path.exists(dev_conf):
        config_files = [dev_conf]

    try:
        cli.main(argv=sys.argv, config_files=config_files)
    except ConfigFilesNotFoundError:
        rw_fail_handler()
