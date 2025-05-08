from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, PositiveInt, field_validator

from .util import BinaryDataSource


class TomlConfig:

    def __init__(self, data_source: BinaryDataSource) -> None:
        self._data_source = data_source

    def parse(self) -> Config:
        with self._data_source.open_stream() as stream:
            data_dict = tomllib.load(stream)
        return Config(**data_dict)


class Config(BaseModel):
    input_dir: Path
    output_dir: Path
    archive_dir: Path
    error_dir: Path
    log_file: Path
    max_retry: PositiveInt
    batch_size: PositiveInt

    @field_validator("input_dir", "output_dir", "archive_dir", "error_dir", mode="after")
    @classmethod
    def make_directory_if_not_exist(cls, v: Path) -> Path:
        if not v.is_dir():
            v.mkdir(parents=True, exist_ok=True)
            print(f"ディレクトリを作成しました: {v}")
        return v

    @field_validator("log_file", mode="after")
    @classmethod
    def make_file_if_not_exist(cls, v: Path) -> Path:
        if not v.is_file():
            v.touch(exist_ok=True)
            print(f"ファイルを作成しました: {v}")
        return v
