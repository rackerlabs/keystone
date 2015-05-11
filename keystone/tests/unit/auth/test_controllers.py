# Copyright 2015 IBM Corp.

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

import uuid

import mock
from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslo_utils import importutils
from oslotest import mockpatch
import stevedore

from keystone.auth import controllers
from keystone.tests import unit


class TestControllers(unit.BaseTestCase):
    def test_load_auth_method_entrypoint_works(self):
        method = uuid.uuid4().hex
        plugin_name = self.getUniqueString()

        # Register the method using the given plugin
        cf = self.useFixture(config_fixture.Config())
        cf.register_opt(cfg.StrOpt(method), group='auth')
        cf.config(group='auth', **{method: plugin_name})

        # Setup stevedore.DriverManager to return a driver for the plugin

        # stevedore.DriverManager returns an object with a `driver` attribute.
        fake_driver_manager = mock.Mock()
        driver_sentinel = object()
        fake_driver_manager.driver = driver_sentinel

        driver_manager_mock = self.useFixture(mockpatch.PatchObject(
            stevedore, 'DriverManager', return_value=fake_driver_manager)).mock

        driver = controllers.load_auth_method(method)

        exp_namespace = 'keystone.auth.%s' % method
        driver_manager_mock.assert_called_once_with(exp_namespace, plugin_name,
                                                    invoke_on_load=True)

        self.assertIs(driver, driver_sentinel)

    def test_load_auth_method_entrypoint_fails_import_works(self):
        method = uuid.uuid4().hex
        plugin_name = self.getUniqueString()

        # Register the method using the given plugin
        cf = self.useFixture(config_fixture.Config())
        cf.register_opt(cfg.StrOpt(method), group='auth')
        cf.config(group='auth', **{method: plugin_name})

        # stevedore.DriverManager raises RuntimeError if it can't load the
        # driver.
        self.useFixture(mockpatch.PatchObject(
            stevedore, 'DriverManager', side_effect=RuntimeError))

        driver_sentinel = object()
        self.useFixture(mockpatch.PatchObject(importutils, 'import_object',
                                              return_value=driver_sentinel))

        driver = controllers.load_auth_method(method)
        self.assertIs(driver, driver_sentinel)

    def test_load_auth_method_entrypoint_fails_import_fails(self):
        method = uuid.uuid4().hex
        plugin_name = self.getUniqueString()

        # Register the method using the given plugin
        cf = self.useFixture(config_fixture.Config())
        cf.register_opt(cfg.StrOpt(method), group='auth')
        cf.config(group='auth', **{method: plugin_name})

        # stevedore.DriverManager raises RuntimeError if it can't load the
        # driver.
        self.useFixture(mockpatch.PatchObject(
            stevedore, 'DriverManager', side_effect=RuntimeError))

        class TestException(Exception):
            pass

        self.useFixture(mockpatch.PatchObject(
            importutils, 'import_object', side_effect=TestException))

        self.assertRaises(TestException, controllers.load_auth_method, method)
