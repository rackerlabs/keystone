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

import mock
import os
import uuid

from oslo_config import generator

import keystone.conf
from keystone.tests import unit


CONF = keystone.conf.CONF


class ConfigTestCase(unit.TestCase):

    def config_files(self):
        config_files = super(ConfigTestCase, self).config_files()

        sample_file = 'keystone.conf.sample'
        args = ['--namespace', 'keystone', '--output-file',
                unit.dirs.etc(sample_file)]
        generator.main(args=args)
        config_files.insert(0, unit.dirs.etc(sample_file))
        self.addCleanup(os.remove, unit.dirs.etc(sample_file))
        return config_files

    def test_config_default(self):
        self.assertIsNone(CONF.auth.password)
        self.assertIsNone(CONF.auth.token)

    def test_profiler_config_default(self):
        """Check config.set_config_defaults() has set [profiler]enabled."""
        self.assertEqual(False, CONF.profiler.enabled)


class DeprecatedTestCase(unit.TestCase):
    """Test using the original (deprecated) name for renamed options."""

    def config_files(self):
        config_files = super(DeprecatedTestCase, self).config_files()
        config_files.append(unit.dirs.tests_conf('deprecated.conf'))
        return config_files

    def test_sql(self):
        # Options in [sql] were moved to [database] in Icehouse for the change
        # to use oslo-incubator's db.sqlalchemy.sessions.

        self.assertEqual('sqlite://deprecated', CONF.database.connection)
        self.assertEqual(54321, CONF.database.idle_timeout)


class DeprecatedOverrideTestCase(unit.TestCase):
    """Test using the deprecated AND new name for renamed options."""

    def config_files(self):
        config_files = super(DeprecatedOverrideTestCase, self).config_files()
        config_files.append(unit.dirs.tests_conf('deprecated_override.conf'))
        return config_files

    def test_sql(self):
        # Options in [sql] were moved to [database] in Icehouse for the change
        # to use oslo-incubator's db.sqlalchemy.sessions.

        self.assertEqual('sqlite://new', CONF.database.connection)
        self.assertEqual(65432, CONF.database.idle_timeout)


class MutableConfigTest(unit.TestCase):

    def config_files(self):
        config_files = super(MutableConfigTest, self).config_files()

        self.config_file = 'keystone.conf.%s' % uuid.uuid4().hex
        self._generate_config()
        config_files.insert(0, unit.dirs.etc(self.config_file))
        self.addCleanup(os.remove, unit.dirs.etc(self.config_file))

        keystone.conf.configure()
        self.assertIsNotNone(keystone.conf.LAST_LOADED)

        return config_files

    def _generate_config(self):
        args = ['--namespace', 'keystone', '--output-file',
                unit.dirs.etc(self.config_file)]
        generator.main(args=args)

    def test_no_update(self):
        # Since file has not been updated since loading config,
        # mutate_config_files doesn't get called on CONF.
        last_loaded = keystone.conf.LAST_LOADED
        with mock.patch(
                'oslo_config.cfg.ConfigOpts.mutate_config_files') as m:
            keystone.conf.mutate_config()
            m.assert_not_called()
        self.assertEqual(last_loaded, keystone.conf.LAST_LOADED)

    def test_update(self):
        # We regenerate the config file, changing the modified time.
        self._generate_config()
        last_loaded = keystone.conf.LAST_LOADED
        # Verify that mutate_config_files on CONF is called and that
        # keystone.conf.LAST_LOADED is updated.
        with mock.patch(
                'oslo_config.cfg.ConfigOpts.mutate_config_files') as m:
            keystone.conf.mutate_config()
            m.assert_called()
        self.assertIsNot(last_loaded, keystone.conf.LAST_LOADED)
