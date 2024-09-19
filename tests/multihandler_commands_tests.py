import pytest
from unittest.mock import MagicMock, patch
from Modules.multi_handler_commands import MultiHandlerCommands
import ssl
import colorama

@pytest.fixture
def multi_handler_commands():
    with patch('Modules.multi_handler_commands.DatabaseClass') as MockDatabaseClass:
        mock_db_instance = MockDatabaseClass.return_value
        mock_db_instance.cursor = MagicMock()
        return MultiHandlerCommands()

@patch('builtins.input', side_effect=["exit"])
def test_current_client_exit(mock_input, multi_handler_commands):
    conn = MagicMock(spec=ssl.SSLSocket)
    r_address = ('127.0.0.1', 12345)
    multi_handler_commands.current_client(conn, r_address)
    assert mock_input.call_count == 1

@patch('builtins.input', side_effect=["shell", "exit"])
def test_current_client_shell(mock_input, multi_handler_commands):
    conn = MagicMock(spec=ssl.SSLSocket)
    r_address = ('127.0.0.1', 12345)
    multi_handler_commands.current_client(conn, r_address)
    assert mock_input.call_count == 2
    multi_handler_commands.sessioncommands.shell.assert_called_once_with(conn, r_address)

@patch('builtins.input', side_effect=["close"])
def test_current_client_close(mock_input, multi_handler_commands):
    conn = MagicMock(spec=ssl.SSLSocket)
    r_address = ('127.0.0.1', 12345)
    multi_handler_commands.current_client(conn, r_address)
    multi_handler_commands.sessioncommands.close_connection.assert_called_once_with(conn, r_address)

def test_listconnections_no_connections(multi_handler_commands):
    with patch('builtins.print') as mock_print:
        multi_handler_commands.listconnections([])
        mock_print.assert_called_once_with(colorama.Fore.RED + "No Active Sessions")

def test_listconnections_with_connections(multi_handler_commands):
    connectionaddress = [('127.0.0.1', 12345)]
    with patch('Modules.multi_handler_commands.connectionaddress', connectionaddress), \
            patch('Modules.multi_handler_commands.hostname', ['localhost']), \
            patch('Modules.multi_handler_commands.operatingsystem', ['Linux']):
        with patch('builtins.print') as mock_print:
            multi_handler_commands.listconnections(connectionaddress)
            mock_print.assert_any_call('Sessions:')
            mock_print.assert_any_call('\x1b[32m0: 127.0.0.1:12345 - localhost - Linux')

@patch('builtins.input', side_effect=["0"])
def test_sessionconnect_valid_client(mock_input, multi_handler_commands):
    conn = MagicMock(spec=ssl.SSLSocket)
    r_address = [('127.0.0.1', 12345)]
    multi_handler_commands.sessionconnect(r_address, r_address)
    multi_handler_commands.current_client.assert_called_once_with(conn, r_address[0])

@patch('Modules.multi_handler_commands.hashfile', return_value=None)
def test_localDatabaseHash_file(mock_hashfile, multi_handler_commands):
    with patch('builtins.input', return_value='file'):
        multi_handler_commands.localDatabaseHash()

@patch('Modules.multi_handler_commands.hashfile', return_value=None)
def test_hashfile(mock_hashfile, multi_handler_commands):
    multi_handler_commands.hashfile('file')
    mock_hashfile.assert_called_once_with('file')

def test_addHashToDatabase(multi_handler_commands):
    with patch.object(multi_handler_commands, 'database') as mock_database:
        multi_handler_commands.addHashToDatabase('file', 'hashedFile')
        mock_database.insert_entry.assert_called_once_with('Hashes', '"file","hashedFile"')
