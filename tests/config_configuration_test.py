import unittest
from unittest.mock import patch
import os
from Server.Modules.utils.config_configuration import (
    config_menu,
)


class TestConfigMenu(unittest.TestCase):

    @patch('builtins.input', side_effect=["1", "3"])
    @patch('builtins.print')
    @patch('src.Server.Modules.config_configuration.TomlFiles.update_config')
    @patch('src.Server.Modules.config_configuration.CONFIG_FILE_PATH',
           os.path.abspath('src/Server/config.toml'))
    def test_config_menu_show_config(self, mock_update_config, mock_print,
                                     mock_input):
        config_menu()
        self.assertEqual(mock_input.call_count, 2)

# TODO: Add more tests
