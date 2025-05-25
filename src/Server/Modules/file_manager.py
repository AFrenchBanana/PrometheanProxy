import os
from .content_handler import JsonFiles


class FileManagerClass:
    def __init__(self, config, uuid) -> None:
        self.directoryTraversalFile = {}
        self.config = config

    def list_files(self, data, target_path) -> None:
        if self.directoryTraversalFile == {}:
            self.directoryTraversalFile = JsonFiles("./directory_traversal.json")

            # self.directoryTraversalFile = JsonFiles(self.config['server']['ImplantData'] + f"/{self.uuid}/directory_traversal.json")

        """
        Traverses the loaded directory data (JSON) to find the contents
        (files and directories) at a specified target path.

        Args:
            data (dict): The dictionary containing the parsed directory traversal data.
            target_path (str): The absolute path to search for (e.g., "C:\\Users" or "/home/user").
                            Uses OS-specific path separators.

        Returns:
            dict: A dictionary with 'files' and 'directories' lists for the target path,
                or None if the path is not found.
        """
        # Normalize path separators and split into components
        normalized_path = os.path.normpath(target_path)
        path_components = []
        head = normalized_path
        while head and head != os.sep and head != os.path.splitdrive(head)[0]:
            head, tail = os.path.split(head)
            if tail:
                path_components.insert(0, tail)
            else: # Handle root drive like C:
                path_components.insert(0, head)
                break

        # Handle root drive specifically if it's the first component
        if os.path.splitdrive(normalized_path)[0]:
            drive = os.path.splitdrive(normalized_path)[0]
            if drive.endswith(':'): # For Windows drives like C:
                path_components[0] = drive # Replace the first component with the full drive name
            else: # For Unix roots like /
                # The split logic might already handle this, but ensure it's correct
                pass
            
        current_node = data
        found_path = True

        # Check if the root of the JSON matches the first path component
        # The C++ code's root JSON structure doesn't explicitly name the root directory,
        # it just contains its 'directories' and 'files'.
        # We assume 'data' itself represents the root of the traversal.
        # If the user provides a path like "C:\\Users", we need to ensure the
        # first component "C:" is implicitly handled as the root of the JSON.

        # If the first component is a drive letter (e.g., 'C:'), we assume the JSON
        # 'data' is the content of that drive.
        # If the path starts with a drive letter, we effectively skip matching the
        # first component against a named directory in the JSON, as the JSON's root
        # already represents that drive.

        start_index = 0
        if path_components and os.path.splitdrive(normalized_path)[0]:
            # If the target path has a drive, assume the JSON's root is that drive.
            # We don't need to find a 'C:' directory *inside* the JSON's root.
            # So, we start matching from the second component.
            # This is a simplification based on the C++ output structure.
            start_index = 1


        for i in range(start_index, len(path_components)):
            component = path_components[i]
            found_component_in_node = False
            if "directories" in current_node:
                for subdir_entry in current_node["directories"]:
                    if subdir_entry.get("name") == component:
                        current_node = subdir_entry.get("contents", {})
                        found_component_in_node = True
                        break
            if not found_component_in_node:
                found_path = False
                break

        if found_path:
            return {
                "files": current_node.get("files", []),
                "directories": [d.get("name") for d in current_node.get("directories", [])]
            }
        else:
            return None
