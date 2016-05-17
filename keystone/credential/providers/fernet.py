from cryptography.fernet import Fernet

from oslo_config import cfg
from oslo_log import log

from keystone.credential.providers import core


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Provider(core.Provider):

    def get_encryption_key(self):
        return CONF.credential.encryption_key

    def get_decryption_key(self):
        return CONF.credential.decryption_key

    def encrypt(self, data):
        f = Fernet(self.get_encryption_key())
        return f.encrypt(data.encode('utf-8'))

    def decrypt(self, token):
        keys = [self.get_encryption_key(), self.get_decryption_key()]

        for key in keys:
            try:
                f = Fernet(key)
                return f.decrypt(str(token)).decode('utf-8')
            except:
                pass

        raise Exception('Could not decrypt credentials')
