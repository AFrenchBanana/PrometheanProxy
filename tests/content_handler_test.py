import unittest
from unittest.mock import mock_open, patch
from tomlkit import parse, dumps
from Server.Modules.utils.content_handler import TomlFiles


class TestTomlFiles(unittest.TestCase):

    def setUp(self):
        # Sample TOML content for testing
        self.toml_content = """
        [section]
        key = "value"
        """
        self.filename = "test_config.toml"

    @patch("builtins.open", new_callable=mock_open,
           read_data='[section]\nkey="value"')
    def test_init(self, mock_open):
        # Test initialization and reading from file
        toml_file = TomlFiles(self.filename)
        mock_open.assert_called_once_with(self.filename,
                                          "rt", encoding="utf-8")
        self.assertIn("section", toml_file.data)
        self.assertEqual(toml_file.data["section"]["key"], "value")

    @patch("builtins.open", new_callable=mock_open,
           read_data='[section]\nkey="value"')
    def test_update_config(self, mock_open):
        # Test updating configuration and saving
        toml_file = TomlFiles(self.filename)
        with patch.object(toml_file, 'save', return_value=None) as mock_save:
            toml_file.update_config("section", "key", "new_value")
            self.assertEqual(toml_file.data["section"]["key"], "new_value")
            mock_save.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    def test_save(self, mock_open):
        # Test saving updated data to file
        toml_file = TomlFiles(self.filename)
        toml_file.data = parse(self.toml_content)
        toml_file.data["section"]["key"] = "new_value"
        toml_file.save()

        # Check if the file was opened in write mode with the correct arguments
        mock_open.assert_any_call(self.filename, "wt", encoding="utf-8")
        handle = mock_open()
        handle.write.assert_called_once_with(dumps(toml_file.data))

    @patch("builtins.open", new_callable=mock_open,
           read_data='[section]\nkey="value"')
    def test_context_manager(self, mock_open):
        # Test context manager methods
        with TomlFiles(self.filename) as data:
            self.assertIn("section", data)
            self.assertEqual(data["section"]["key"], "value")
        # Ensure file is not explicitly closed
        mock_open().close.assert_not_called()
