import abc
import six

from keystone.common import dependency


@dependency.provider('credential_provider_api')
@six.add_metaclass(abc.ABCMeta)
class Provider(object):

    @abc.abstractmethod
    def get_encryption_key(self):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_decryption_key(self):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def encrypt(self, data):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def decrypt(self, token):
        raise exception.NotImplemented()  # pragma: no cover
