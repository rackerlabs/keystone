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

import abc

import six

from keystone import exception


@six.add_metaclass(abc.ABCMeta)
class FernetUtilsDriver(object):

    @abc.abstractmethod
    def validate_key_repository():
        """Validate permissions on the key repository directory."""
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def create_key_directory():
        """Attempt to create the key directory.

        Create key directory if it doesn't exist and if it is necessary.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def initialize_key_repository():
        """Create a key repository and bootstrap it with a key."""
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def rotate_keys():
        """Create a new primary key and revoke excess active keys.

        Key rotation utilizes the following behaviors:

        - The highest key number is used as the primary key (used for
          encryption).
        - All keys can be used for decryption.
        - New keys are always created as key "0," which serves as a placeholder
          before promoting it to be the primary key.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def load_keys():
        """Load keys from repository into a list.

        The first key in the list is the primary key used for encryption. All
        other keys are active secondary keys that can be used for decrypting
        tokens.
        """
        raise exception.NotImplemented()  # pragma: no cover
