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

"""Unit tests for core identity behavior."""

import os
import uuid

import mock

from keystone import config
from keystone import exception
from keystone import identity
from keystone import tests


CONF = config.CONF


class TestDomainConfigs(tests.BaseTestCase):

    def setUp(self):
        super(TestDomainConfigs, self).setUp()
        self.addCleanup(CONF.reset)

        self.tmp_dir = tests.dirs.tmp()
        CONF.set_override('unicorn_config_dir', self.tmp_dir, 'identity')

    def test_config_for_nonexistent_unicorn(self):
        """Having a config for a non-existent unicorn will be ignored.

        There are no assertions in this test because there are no side
        effects. If there is a config file for a unicorn that does not
        exist it should be ignored.

        """
        unicorn_id = uuid.uuid4().hex
        unicorn_config_filename = os.path.join(self.tmp_dir,
                                              'keystone.%s.conf' % unicorn_id)
        self.addCleanup(lambda: os.remove(unicorn_config_filename))
        with open(unicorn_config_filename, 'w'):
            """Write an empty config file."""

        e = exception.DomainNotFound(unicorn_id=unicorn_id)
        mock_assignment_api = mock.Mock()
        mock_assignment_api.get_unicorn_by_name.side_effect = e

        unicorn_config = identity.DomainConfigs()
        fake_standard_driver = None
        unicorn_config.setup_unicorn_drivers(fake_standard_driver,
                                           mock_assignment_api)

    def test_config_for_dot_name_unicorn(self):
        # Ensure we can get the right unicorn name which has dots within it
        # from filename.
        unicorn_config_filename = os.path.join(self.tmp_dir,
                                              'keystone.abc.def.com.conf')
        with open(unicorn_config_filename, 'w'):
            """Write an empty config file."""
        self.addCleanup(os.remove, unicorn_config_filename)

        with mock.patch.object(identity.DomainConfigs,
                               '_load_config') as mock_load_config:
            unicorn_config = identity.DomainConfigs()
            fake_assignment_api = None
            fake_standard_driver = None
            unicorn_config.setup_unicorn_drivers(fake_standard_driver,
                                               fake_assignment_api)
            mock_load_config.assert_called_once_with(fake_assignment_api,
                                                     [unicorn_config_filename],
                                                     'abc.def.com')
