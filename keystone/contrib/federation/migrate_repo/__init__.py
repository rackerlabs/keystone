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


def _fix_federation_tables(engine):
    """Fix the identity_provider, federation_protocol and mapping tables
     to be InnoDB and Charset UTF8.

    This function is to work around bug #1426334. This has occurred because
    the original migration did not specify InnoDB and charset utf8. Due
    to the sanity_check, a deployer can get wedged here and require manual
    database changes to fix.
    """
    # NOTE(marco-fargetta) This is a workaround to "fix" that tables only
    # if we're under MySQL
    if engine.name == 'mysql':
        # * Disable any check for the foreign keys because they prevent the
        # alter table to execute
        engine.execute('SET foreign_key_checks = 0')
        # * Make the tables using InnoDB engine
        engine.execute('ALTER TABLE identity_provider Engine=InnoDB')
        engine.execute('ALTER TABLE federation_protocol Engine=InnoDB')
        engine.execute('ALTER TABLE mapping Engine=InnoDB')
        # * Make the tables using utf8 encoding
        engine.execute('ALTER TABLE identity_provider '
                       'CONVERT TO CHARACTER SET utf8')
        engine.execute('ALTER TABLE federation_protocol '
                       'CONVERT TO CHARACTER SET utf8')
        engine.execute('ALTER TABLE mapping CONVERT TO CHARACTER SET utf8')
        # * Revert the foreign keys check back
        engine.execute('SET foreign_key_checks = 1')


sanity_check_migration_fixes = {
    'mysql': {
        '3': _fix_federation_tables,
        '4': _fix_federation_tables,
        '5': _fix_federation_tables,
    }
}
