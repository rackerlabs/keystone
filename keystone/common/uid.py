import uuid

from keystone import config
from keystone import exception


CONF = config.CONF

# constrained by the lengths of what each driver will support as an ID value
MIN_LENGTH = 1
MAX_LENGTH = 64


def new(length=None, min_length=MIN_LENGTH):
    """Return a URL-friendly globally unique string.

    - URL-friendliness: encoding/decoding is not required to use the string in
      a URL.
    - Globally unique: with pow(16, length) possible variations; lower lengths
      are more likely to produce collisions are not are not recommended to
      ensure uniqueness in a production system.

    :param length: the requested length of the string; defaults to the greater
                   of either `min_length` or `keystone.conf [DEFAULT]
                   uid_length` if not specified
    :param min_length: useful for constraining the minimum UID length above the
                       user specified minimum
    :returns: unique identifier string
    :raises: keystone.exception.ValidationError if the requested `length` falls
             outside of the range of `MIN_LENGTH` and `MAX_LENGTH`

    """
    length = length or max(min_length, CONF.uid_length)

    if length < MIN_LENGTH or length > MAX_LENGTH:
        raise exception.ValidationError(
            _('Specified UID length is not in the acceptable range: '
              '%(min_length)s-%(max_length)s.') % {
                  'min_length': MIN_LENGTH,
                  'max_length': MAX_LENGTH})

    s = ''
    while length > len(s):
        s += uuid.uuid4().hex
    return s[:length]
