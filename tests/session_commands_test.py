from src.Server.Modules.sessions_commands import SessionCommandsClass
from src.Server.Modules.global_objects import send_data
import unittest
import ssl
from unittest.mock import MagicMock


class TestSessionCommands(unittest.TestCase):

    def test_close_connection(self):
        session = SessionCommandsClass()
        conn = MagicMock(spec=ssl.SSLSocket)
        r_address = ("127.0.0.1", 8080)
        with unittest.mock.patch('builtins.input', return_value='y'):
            session.close_connection(conn, r_address)
        send_data.assert_called_once_with(r_address, "shutdown")
        conn.close.assert_called_once()
