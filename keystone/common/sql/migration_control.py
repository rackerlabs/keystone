# Copyright 2016 OpenStack Foundation
# All Rights Reserved.
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

# NOTE(henry-nash): At the start of a new release cycle, the following must be
# undertaken to enable migrations:
#
# - Add a new release name definition below, add it to the release sequence and
#   mark it as the LATEST_RELEASE
# - Add a repo with the name of the release in common/sql/migrate_repo_contract
#   to hold any contract migrations that safe to run in after upgrading to the
#   new release (e.g. removing columns from which data was migrated in the
#   previous release)
#

NO_RELEASE = 'None'
EARLIER_RELEASE = 'Pre-Newton'
NEWTON_RELEASE = 'Newton'
OCATA_RELEASE = 'Ocata'

LATEST_RELEASE = NEWTON_RELEASE

RELEASE_SEQUENCE = [EARLIER_RELEASE, NEWTON_RELEASE, OCATA_RELEASE]
