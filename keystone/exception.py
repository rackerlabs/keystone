# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

from keystone.common import config
from keystone.common import logging
from keystone.openstack.common.gettextutils import _  # noqa


CONF = config.CONF
LOG = logging.getLogger(__name__)

# Tests use this to make exception message format errors fatal
_FATAL_EXCEPTION_FORMAT_ERRORS = False


class Error(StandardError):
    """Base error class.

    Child classes should define an HTTP status code, title, and a
    msg_format.

    """
    code = None
    title = None
    msg_format = None

    def __init__(self, message=None, **kwargs):
        try:
            message = self._build_message(message, **kwargs)
        except KeyError:
            # if you see this warning in your logs, please raise a bug report
            if _FATAL_EXCEPTION_FORMAT_ERRORS:
                raise
            else:
                LOG.warning(_('missing exception kwargs (programmer error)'))
                message = self.msg_format

        super(Error, self).__init__(message)

    def _build_message(self, message, **kwargs):
        """Builds and returns an exception message.

        :raises: KeyError given insufficient kwargs

        """
        if not message:
            message = self.msg_format % kwargs
        return message


class ValidationError(Error):
    msg_format = _("Expecting to find %(attribute)s in %(target)s."
                   " The server could not comply with the request"
                   " since it is either malformed or otherwise"
                   " incorrect. The client is assumed to be in error.")
    code = 400
    title = 'Bad Request'


class StringLengthExceeded(ValidationError):
    msg_format = _("String length exceeded.The length of"
                   " string '%(string)s' exceeded the limit"
                   " of column %(type)s(CHAR(%(length)d)).")


class ValidationSizeError(Error):
    msg_format = _("Request attribute %(attribute)s must be"
                   " less than or equal to %(size)i. The server"
                   " could not comply with the request because"
                   " the attribute size is invalid (too large)."
                   " The client is assumed to be in error.")
    code = 400
    title = 'Bad Request'


class SecurityError(Error):
    """Avoids exposing details of security failures, unless in debug mode."""

    def _build_message(self, message, **kwargs):
        """Only returns detailed messages in debug mode."""
        if CONF.debug:
            return message or self.msg_format % kwargs
        else:
            return self.msg_format % kwargs


class Unauthorized(SecurityError):
    msg_format = _("The request you have made requires authentication.")
    code = 401
    title = 'Unauthorized'


class AuthPluginException(Unauthorized):
    msg_format = _("Authentication plugin error.")

    def __init__(self, *args, **kwargs):
        super(AuthPluginException, self).__init__(*args, **kwargs)
        self.authentication = {}


class AuthMethodNotSupported(AuthPluginException):
    msg_format = _("Attempted to authenticate with an unsupported method.")

    def __init__(self, *args, **kwargs):
        super(AuthMethodNotSupported, self).__init__(*args, **kwargs)
        self.authentication = {'methods': CONF.auth.methods}


class AdditionalAuthRequired(AuthPluginException):
    msg_format = _("Additional authentications steps required.")

    def __init__(self, auth_response=None, **kwargs):
        super(AdditionalAuthRequired, self).__init__(message=None, **kwargs)
        self.authentication = auth_response


class Forbidden(SecurityError):
    msg_format = _("You are not authorized to perform the requested action.")
    code = 403
    title = 'Forbidden'


class ForbiddenAction(Forbidden):
    msg_format = _("You are not authorized to perform the"
                   " requested action, %(action)s.")


class NotFound(Error):
    msg_format = _("Could not find, %(target)s.")
    code = 404
    title = 'Not Found'


class EndpointNotFound(NotFound):
    msg_format = _("Could not find endpoint, %(endpoint_id)s.")


class MetadataNotFound(NotFound):
    """(dolph): metadata is not a user-facing concept,
    so this exception should not be exposed"""

    msg_format = _("An unhandled exception has occurred:"
                   " Could not find metadata.")


class PolicyNotFound(NotFound):
    msg_format = _("Could not find policy, %(policy_id)s.")


class RoleNotFound(NotFound):
    msg_format = _("Could not find role, %(role_id)s.")


class ServiceNotFound(NotFound):
    msg_format = _("Could not find service, %(service_id)s.")


class DomainNotFound(NotFound):
    msg_format = _("Could not find domain, %(domain_id)s.")


class ProjectNotFound(NotFound):
    msg_format = _("Could not find project, %(project_id)s.")


class TokenNotFound(NotFound):
    msg_format = _("Could not find token, %(token_id)s.")


class UserNotFound(NotFound):
    msg_format = _("Could not find user, %(user_id)s.")


class GroupNotFound(NotFound):
    msg_format = _("Could not find group, %(group_id)s.")


class TrustNotFound(NotFound):
    msg_format = _("Could not find trust, %(trust_id)s.")


class CredentialNotFound(NotFound):
    msg_format = _("Could not find credential, %(credential_id)s.")


class VersionNotFound(NotFound):
    msg_format = _("Could not find version, %(version)s.")


class Conflict(Error):
    msg_format = _("Conflict occurred attempting to store %(type)s."
                   " %(details)s")
    code = 409
    title = 'Conflict'


class RequestTooLarge(Error):
    msg_format = _("Request is too large.")
    code = 413
    title = 'Request is too large.'


class UnexpectedError(Error):
    msg_format = _("An unexpected error prevented the server"
                   " from fulfilling your request. %(exception)s")
    code = 500
    title = 'Internal Server Error'


class MalformedEndpoint(UnexpectedError):
    msg_format = _("Malformed endpoint URL (%(endpoint)s),"
                   " see ERROR log for details.")


class NotImplemented(Error):
    msg_format = _("The action you have requested has not been implemented.")
    code = 501
    title = 'Not Implemented'


class PasteConfigNotFound(UnexpectedError):
    msg_format = _("The Keystone paste configuration file"
                   " %(config_file)s could not be found.")
