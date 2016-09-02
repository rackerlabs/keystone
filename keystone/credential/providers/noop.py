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


from keystone.credential.providers import core


class Provider(core.Provider):
    def encrypt(self, credential):
        """Attempt to encrypt a plaintext credential.

        :param credential: a plaintext representation of a credential
        :returns: an encrypted credential
        """
        return (credential, "")

    def decrypt(self, credential):
        """Attempt to decrypt a credential.

        :param credential: an encrypted credential string
        :returns: a decrypted credential
        """
        return credential
