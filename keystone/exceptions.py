import re
import json
import webob


class KeystoneError(StandardError):
    """Base error class.

    Child classes should define an HTTP status code, title, and a doc string.

    """
    code = None
    title = None

    def __init__(self, *args, **kwargs):
        """Use the doc string as the error message"""
        super(KeystoneError, self).__init__(self.__doc__, *args, **kwargs)

    def response(self):
        """Forms a WSGI response based on the current error"""
        resp = webob.Response()
        resp.status = "%s %s" % (self.code, self.title)
        resp.headerlist = [('Content-Type', 'application/json')]

        body = {
                "error": {
                    "code": self.code,
                    "title": self.title,
                    "message": str(self)}}
        resp.body = json.dumps(body)

        return resp

    def __str__(self):
        """Cleans up line breaks and indentation from doc strings."""
        string = super(KeystoneError, self).__str__()
        string = re.sub('[ \n]+', ' ', string)
        string = string.strip()
        return string


class ValidationError(KeystoneError):
    """Expecting %(attribute)s: The server could not comply with the request
    since it is either malformed or otherwise incorrect.

    The client is assumed to be in error.
    """
    code = 400
    title = 'Bad Request'

    def __init__(self, attr):
        msg = self.__doc__ % {"attribute": attr}
        super(Unauthorized, self).__init__(msg)


class Unauthorized(KeystoneError):
    """The request you have made requires authentication.

    Make your request again with an X-Auth-Token header containing your auth
    token ID.

    """
    code = 401
    title = 'Not Authorized'


class Forbidden(KeystoneError):
    """Your X-Auth-Token is not authorized to perform the requested action."""
    code = 403
    title = 'Not Authorized'


class NotFound(KeystoneError):
    """The expected %(object)s was not found."""
    code = 404
    title = 'Not Found'

    def __init__(self, obj):
        msg = self.__doc__ % {"object": obj}
        super(NotFound, self).__init__(msg)
