# Copyright 2014 Mirantis.inc
# All Rights Reserved.
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


DB_INIT_VERSION = 33


def _fix_migration_37(engine):
    """Fix the region table to be InnoDB and Charset UTF8.

    This function is to work around bug #1334779. This has occurred because
    the original migration 37 did not specify InnoDB and charset utf8. Due
    to the sanity_check, a deployer can get wedged here and require manual
    database changes to fix.
    """
    # * Make sure the engine is InnoDB
    engine.execute('ALTER TABLE region Engine=InnoDB')
    # * Make sure the character set is utf8
    engine.execute('ALTER TABLE region CONVERT TO CHARACTER SET utf8')


sanity_check_migration_fixes = {
    'mysql': {
        '37': _fix_migration_37,
    }
}
