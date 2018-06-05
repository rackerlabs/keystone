# Copyright 2012 OpenStack Foundation
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

import abc

import six

from keystone import exception


@six.add_metaclass(abc.ABCMeta)
class Provider(object):
    """Interface description for a Receipt provider."""

    @abc.abstractmethod
    def get_receipt_version(self, receipt_data):
        """Return the version of the given receipt data.

        If the given receipt data is unrecognizable,
        UnsupportedReceiptVersionException is raised.

        :param receipt_data: receipt_data
        :type receipt_data: dict
        :returns: receipt version string
        :raises keystone.exception.UnsupportedReceiptVersionException:
            If the receipt version is not expected.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def issue_receipt(self, user_id, method_names, issued_at):
        """Issue a Receipt.

        :param user_id: identity of the user
        :type user_id: string
        :param method_names: names of authentication methods
        :type method_names: list
        :param issued_at: time the receipt was issued at
        :type issued_at: string
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def validate_receipt(self, receipt_ref):
        """Validate the given receipt and return the receipt_data.

        :param receipt_ref: the receipt reference
        :type receipt_ref: dict
        :returns: receipt data
        :raises keystone.exception.ReceiptNotFound:
            If the receipt doesn't exist.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def _get_receipt_id(self, receipt_data):
        """Generate the receipt_id based upon the data in receipt_data.

        :param receipt_data: receipt information
        :type receipt_data: dict
        :returns: receipt identifier
        :rtype: six.text_type
        """
        raise exception.NotImplemented()  # pragma: no cover
