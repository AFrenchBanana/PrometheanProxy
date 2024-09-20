import unittest

from Modules.authentication import Authentication


def authentication():
    return Authentication()


class TestAuthentication(unittest.TestCase):

    def test_get_authentication_string(self):
        auth = authentication()
        auth.get_authentication_string()
        self.assertEqual(len(auth.key), 16)

    def test_create_authentication_response(self):
        auth = authentication()
        auth.get_authentication_string()
        auth.create_authentication_response(12345)
        self.assertEqual(len(auth.auth_key), 128)

    def test_test_auth(self):
        auth = authentication()
        auth.get_authentication_string()
        auth.create_authentication_response(12345)
        self.assertTrue(auth.test_auth(auth.auth_key, 12345))
