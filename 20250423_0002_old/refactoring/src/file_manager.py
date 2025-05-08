import logging
from pathlib import Path

from .config import Config

logger = logging.getLogger("Log")


class FileManager:

    def __init__(self, config: Config) -> None:
        self._config = config

    def list_input_files(self, pattern: str = "*.csv") -> list[Path]:
        file_paths = [
            path
            for path in self._config.input_dir.glob("*.csv")
            if path.is_file()
        ]
