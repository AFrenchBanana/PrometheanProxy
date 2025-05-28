
import zlib
import json

from Modules.global_objects import logger


def process_request_data(raw_data: bytes) -> tuple[dict | None, str | None]:
    """
    Decompresses and decodes JSON data from a request.
    Handles both compressed (zlib) and uncompressed data.

    Args:
        raw_data: The raw data from the request.

    Returns:
        A tuple containing the parsed data (dict) and an error message (str).
        If successful, the error message is None. If it fails, the data is None.
    """
    try:
        decompressed_data = zlib.decompress(raw_data)
        data = json.loads(decompressed_data.decode('utf-8'))
        logger.debug(f"Successfully decompressed data. Original size: {len(raw_data)} bytes, Decompressed size: {len(decompressed_data)} bytes")
        return data, None
    except zlib.error:
        logger.debug("Data is not compressed, parsing as plain JSON.")
        try:
            data = json.loads(raw_data.decode('utf-8'))
            return data, None
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON data: {e}"
            logger.error(error_msg)
            return None, error_msg
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        error_msg = f"Failed to parse decompressed JSON data: {e}"
        logger.error(error_msg)
        return None, error_msg
