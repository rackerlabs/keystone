# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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


from __future__ import absolute_import

import fixtures
import mox
import stubout


class MoxFixture(fixtures.Fixture):
    """A fixture for using mox in testcases.

    This fixture automatically handles the setup and teardown required by
    mox. To use is you simply create an instance, register it with your
    testcase and use the instance's mox property like any other `mox.Mox`
    instance.

    Example setup:

    def setUp(self):
        fixture = self.useFixture(MoxFixture)
        self.mox = fixture.mox

    """

    def setUp(self):
        super(MoxFixture, self).setUp()
        self.mox = mox.Mox()
        self.addCleanup(self.mox.UnsetStubs)
        self.addCleanup(self.mox.VerifyAll)


class StuboutFixture(fixtures.Fixture):
    """A fixture for using stubout in test cases.

    This fixture automatically handles the setup and teardown required by
    stubout. To use is you simply create an instance, register it with your
    testcase and use the instance's stubs property like any other
    `stubout.StubOutForTesting` instance.

    Example setup:

    def setUp(self):
        fixture = self.useFixture(StuboutFixture)
        self.stubs = fixture.stubs

    """

    def setUp(self):
        super(StuboutFixture, self).setUp()
        self.stubs = stubout.StubOutForTesting()
        self.addCleanup(self.stubs.UnsetAll)
        self.addCleanup(self.stubs.SmartUnsetAll)
