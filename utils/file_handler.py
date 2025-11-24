import json
from .logger import get_logger

logger = get_logger()

def load_json_file(file_path: str):
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"No existing stocks file found in: {file_path}")
        return None
    except json.JSONDecodeError:
        logger.warning(f"Json decode error: {file_path}")
        return None

def append_to_markdown_file(file_path: str, content: str):
    """Append content to a markdown file."""
    try:
        with open(file_path, "a") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Error appending to markdown file {file_path}: {e}")