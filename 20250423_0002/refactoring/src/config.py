from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, PositiveInt

from util import BinaryDataSource


class TomlConfig:

    def __init__(self, data_source: BinaryDataSource):
        self._data_source = data_source

    def parse(self) -> Config:
        with self._data_source.open_stream() as stream:
            data_dict = tomllib.load(stream)
        return Config.model_validate(data_dict)


class Config(BaseModel):
    input_dir: Path
    output_dir: Path
    archive_dir: Path
    error_dir: Path
    log_file: Path
    max_retry: PositiveInt
    batch_size: PositiveInt
