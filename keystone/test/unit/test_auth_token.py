import unittest2 as unittest
import datetime
from dateutil.tz import tzlocal

from keystone.middleware import auth_token as middleware

class TestAuthTokenMiddleware(unittest.TestCase):
    """auth_token middleware unit tests"""

    def test__convert_date(self):
        _convert_date = middleware.AuthProtocol._convert_date
        self.assertRaises(ValueError, _convert_date, 'X')
        self.assertEqual(_convert_date('2000-1-1T13:10:12'),
                         946753812.0)
        self.assertEqual(_convert_date('2000-1-1T13:10:12.1234'),
                         946753812.0)
        self.assertEqual(_convert_date('2000-1-1T13:10:12.1234+06:00'),
                         946753812.0 - (6 * 3600))
        self.assertEqual(_convert_date('2000-1-1T13:10:12.1234-06:00'),
                         946753812.0 + (6 * 3600))

if __name__ == '__main__':
    unittest.main()
