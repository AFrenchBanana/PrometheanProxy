import unittest
from unittest.mock import call, patch, MagicMock
from ssl import SSLSocket
import struct
from src.Server.Modules.global_objects import (
    add_connection_list,
    remove_connection_list,
    send_data, receive_data,
    send_data_loadingbar,
    execute_local_comands,
    tab_compeletion,
    connectiondetails,
    connectionaddress,
    hostname,
)

# Sample data
sample_data = "This is a test message"
sample_data_bytes = sample_data.encode('utf-8')
chunk_size = 4096


class TestGlobalObjects(unittest.TestCase):

    def setUp(self):
        self.conn = MagicMock(spec=SSLSocket)
        self.r_address = ('127.0.0.1', 8080)
        self.host = 'localhost'

    def test_add_connection_list_and_remove(self):
        add_connection_list(self.conn, self.r_address, self.host)
        self.assertIn(self.conn, connectiondetails)
        self.assertIn(self.r_address, connectionaddress)
        self.assertIn(self.host, hostname)
        remove_connection_list(self.r_address)
        self.assertNotIn(self.conn, connectiondetails)
        self.assertNotIn(self.r_address, connectionaddress)
        self.assertNotIn(self.host, hostname)

    def test_send_data(self):
        send_data(self.conn, sample_data)
        expected_calls = [
            call(struct.pack('!II', len(sample_data_bytes), chunk_size)),
            call(sample_data_bytes)
        ]
        self.conn.sendall.assert_has_calls(expected_calls)

    def test_receive_data(self):
        header = struct.pack('!II', len(sample_data_bytes), chunk_size)
        self.conn.recv.side_effect = [header, sample_data_bytes]
        received_data = receive_data(self.conn)
        self.assertEqual(received_data, sample_data)

    def test_send_data_loadingbar(self):
        with patch('tqdm.tqdm', return_value=iter([sample_data_bytes])):
            send_data_loadingbar(self.conn, sample_data)
            self.conn.sendall.assert_any_call(
                struct.pack('!II', len(sample_data_bytes), chunk_size))
            self.conn.sendall.assert_any_call(sample_data_bytes)

    @patch("os.system")
    def test_execute_local_comands(self, mock_system):
        self.assertTrue(execute_local_comands("ls"))
        self.assertTrue(execute_local_comands("\\cat"))
        mock_system.assert_called()

    def test_tab_compeletion(self):
        variables = ['config', 'connection', 'connect']
        self.assertEqual(tab_compeletion('con', 0, variables), 'config')
        self.assertEqual(tab_compeletion('con', 1, variables), 'connection')
        self.assertEqual(tab_compeletion('con', 2, variables), 'connect')
        self.assertIsNone(tab_compeletion('con', 3, variables))
