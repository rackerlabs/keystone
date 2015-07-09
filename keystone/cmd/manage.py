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
    environment.use_stdlib()
    keystone_config_path = '/opt/stack/keystone/etc/keystone.conf'
    keystone_sample_config_path = '/opt/stack/keystone/etc/keystone.conf.sample'

    def continuechecker(aborting):
        continuechecker.exec_main = True
        continuechecker.exec_main = not aborting
        return continuechecker.exec_main

    def keystone_conf_sample_to_conf(sample_path, config_path):
        keystone_conf_sample_to_conf.config_path = config_path
        if os.path.exists(sample_path):
            usr_response = raw_input("keystone.conf will be written to " +
                                     config_path + '\033[33m' + " Any existing "
                                     "file will be overwritten. " + '\033[39m' +
                                     "Is " "this okay?\n(y)es (n)o: ")

            if (usr_response[0].lower() == 'y'):
                write_file = open(config_path, 'w')
                temp = open(sample_path, 'r')
                read_file = temp.read()
                write_file.write(read_file)
                temp.close()
                write_file.close()
                raw_input('\033[32m' + "Write finished successfully. "
                          "Press enter to continue: " + '\033[39m')
                continuechecker(False)

            elif (usr_response[0].lower() == 'n'):
                print('\033[31m' + "Aborting..." + '\033[39m')
                continuechecker(True)

            else:
                print '\033[31m' + " Invalid option. Aborting..." + '\033[39m'
                continuechecker(True)

        else:
            usr_response = raw_input("Warning: path to keystone.conf.sample not"
                                     " valid. You can either reinput path to "
                                     "keystone.conf.sample or abort creating "
                                     "keystone.conf. (r)einput (a)bort: ")

            if (usr_response[0].lower() == 'r'):

                sample_path = raw_input("Please enter correct path for "
                                        "keystone.conf.sample: ")
                keystone_conf_sample_to_conf(sample_path, config_path)
            elif (usr_response[0].lower() == 'a'):
                print '\033[31m' + "Aborting..." + '\033[39m'
                continuechecker(True)
            else:
                print '\033[31m' + "Invalid option. Aborting..." + '\033[39m'
                continuechecker(True)

    def input_parser(usr_response):
        if (usr_response[0].lower() == 'a'):
            print '\033[31m' + "Aborting..." + '\033[39m'
            continuechecker(True)
        elif (usr_response[0].lower() == 'c'):
            keystone_conf_sample_to_conf(keystone_sample_config_path,
                                         keystone_config_path)
        else:
            print ('\033[31m' + "Response not recognized. Aborting..." +
                   '\033[39m')
            continuechecker(True)

    def rw_fail_handler():
        usr_response = raw_input('\033[33m' + "Warning: " + '\033[39m' + "keys"
                                 "tone.conf was not found, or current user doe"
                                 "s not have sufficient privileges to access"
                                 " file.\n (a)bort (c)opy keystone.conf from "
                                 "keystone.conf.sample: ")
        return usr_response

    def test_rw():
        if ((not os.access(keystone_config_path, os.R_OK)) or
                (not os.access(keystone_config_path, os.W_OK))):
                input_parser(rw_fail_handler())
        else:
            continuechecker(False)

    test_rw()

    dev_conf = os.path.join(possible_topdir,
                            'etc',
                            'keystone.conf')
    config_files = None
    if os.path.exists(dev_conf):
        config_files = [dev_conf]

    cli.main(argv=sys.argv, config_files=config_files)
    environment.use_stdlib()
    if (continuechecker.exec_main):
        cli.main(argv=sys.argv, config_files=kcstc)
