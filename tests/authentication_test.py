# tests/authentication_test.py
import unittest
from src.Server.Modules.authentication import Authentication
from src.Server.Modules.global_objects import config


class TestAuthentication(unittest.TestCase):

    def test_get_authentication_string(self):
        auth = Authentication()
        auth.get_authentication_string()
        self.assertEqual(len(auth.key), config['authentication']['keylength'])

    def test_create_authentication_response(self):
        auth = Authentication()
        auth.get_authentication_string()
        auth.create_authentication_response(12345)
        self.assertEqual(len(auth.auth_key), 128)

    def test_test_auth(self):
        auth = Authentication()
        auth.get_authentication_string()
        auth.create_authentication_response(12345)
        self.assertTrue(auth.test_auth(auth.auth_key, 12345))
