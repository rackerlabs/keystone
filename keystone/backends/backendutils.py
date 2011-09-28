from keystone.backends import models
import keystone.backends as backends
import hashlib


def __get_hashed_password(password):
    if password != None and len(password) > 0:
            return __make_password(password)
    else:
        return None


def set_hashed_password(values):
    """
    Sets hashed password for password.
    """
    if backends.SHOULD_HASH_PASSWORD:
        if type(values) is dict and 'password' in values.keys():
            values['password'] = __get_hashed_password(values['password'])
        elif type(values) is models.User:
            values.password = __get_hashed_password(values.password)


def check_password(raw_password, enc_password):
    """
    Compares raw password and encoded password.
    """
    if not raw_password:
        return False
    if backends.SHOULD_HASH_PASSWORD:
        return enc_password == __get_hexdigest(raw_password)
    else:
        return enc_password == raw_password


def __make_password(raw_password):
    """
     Produce a new password string in this format: salt$hash
    """
    if raw_password is None:
        return None
    hsh = __get_hexdigest(raw_password)
    return '%s' % (hsh)


def __get_hexdigest(raw_password):
    salt = backends.HASH_SALT
    return hashlib.sha1(salt + raw_password).hexdigest()
