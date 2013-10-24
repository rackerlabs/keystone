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

    def setUp(self):
        super(MoxFixture, self).setUp()
        self.mox = mox.Mox()
        self.addCleanup(self.mox.UnsetStubs)
        self.addCleanup(self.mox.VerifyAll)


class StuboutFixture(fixtures.Fixture):

    def setUp(self):
        super(StuboutFixture, self).setUp()
        self.stubs = stubout.StubOutForTesting()
        self.addCleanup(self.stubs.UnsetAll)
        self.addCleanup(self.stubs.SmartUnsetAll)
