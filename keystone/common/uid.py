import uuid

from keystone import config
from keystone import exception


CONF = config.CONF

# determined by what the lowest common denominator backend will accept
MIN_LENGTH = 1
MAX_LENGTH = 64


def new(length=None, min_length=MIN_LENGTH):
    length = length or max(min_length, CONF.uid_length)

    if length < MIN_LENGTH or length > MAX_LENGTH:
        raise exception.UnexpectedError(
            _('Specified UID length is not in the acceptable range: '
              '%(min_length)s-%(max_length)s.') % {
                  'min_length': MIN_LENGTH,
                  'max_length': MAX_LENGTH})

    s = ''
    while length > len(s):
        s += uuid.uuid4().hex
    return s[:length]
