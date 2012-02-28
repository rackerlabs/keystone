import cStringIO
import gzip

from keystone.common import wsgi


def compress(string):
    """Compresses a string using gzip."""
    buff = cStringIO.StringIO()

    zfile = gzip.GzipFile(fileobj=buff, mode='wb', compresslevel=6)
    zfile.write(string)
    zfile.close()

    return buff.getvalue()


def decompress(string):
    """Decompresses a gzipped string."""
    buff = cStringIO.StringIO(string)

    zfile = gzip.GzipFile(fileobj=buff, mode='rb', compresslevel=6)
    decompressed = zfile.read()
    zfile.close()

    return decompressed


class ContentCompressionMiddleware(wsgi.Middleware):
    """Compresses response content if the client understands GZip compression.

    This should be position first in the WSGI pipeline, so that the
    compression of the response content is the last thing that happens.

    It will NOT compress content if any of the following are true:

        * The request doesn't have an Accept-Encoding header containing gzip.
        * The underlying app has already set the Content-Encoding header.
        * The content body length is less than 200 bytes.

    """
    def process_response(self, request, response):
        # we don't want to compress content if the client doesn't want it
        accept_encoding = request.headers.get('Accept-Encoding')
        if accept_encoding is None or 'gzip' not in accept_encoding:
            return response

        # we don't want to interfere with other middleware
        if response.headers.get('Content-Encoding') is not None:
            return response

        # adding compression to an already small response would make it bigger
        if len(response.body) < 200:
            return response

        response.body = compress(response.body)
        response.headers['Content-Encoding'] = 'gzip'
        return response
