import csv
import logging
from contextlib import contextmanager
from csv import DictReader, DictWriter
from datetime import datetime
from pathlib import Path
from typing import Generator

from config import Config

logger = logging.getLogger(__name__)


class FileManager:

    def __init__(self, config: Config) -> None:
        self._input_dir = config.input_dir
        self._output_dir = config.output_dir
        self._archive_dir = config.archive_dir
        self._error_dir = config.error_dir

    def create_directories_if_not_exist(self) -> None:
        directories = [
            self._input_dir,
            self._output_dir,
            self._archive_dir,
            self._error_dir,
        ]
        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True)
                logger.info(f"ディレクトリを作成しました: {directory}")

    def list_input_files(self, *, pattern: str = "*") -> list[Path]:
        return list(self._input_dir.glob(pattern))

    def move_to_archive(self, input_file: Path) -> None:
        archive_path = self._archive_dir / input_file.name
        input_file.rename(archive_path)
        logger.info(f"ファイルをアーカイブしました: {input_file} -> {archive_path}")

    def move_to_error(self, input_file: Path) -> None:
        error_path = self._error_dir / input_file.name
        input_file.rename(error_path)
        logger.info(f"ファイルをエラーに移動しました: {input_file} -> {error_path}")

    def get_output_path(self, input_file: Path, *, prefix: str = "processed_") -> Path:
        filename = prefix + input_file.name
        return self._output_dir / filename

    def get_summary_report_path(self, *, prefix: str = "summary_report_") -> Path:
        filename = prefix + f"{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"
        return self._output_dir / filename


class CsvHandler:

    @contextmanager
    def open_csv_file(
            self,
            input_file: Path,
            output_file: Path,
            *,
            additional_fields: list[str] = None,
    ) -> Generator[tuple[DictReader[str], DictWriter]]:

        try:
            with open(input_file, "r", encoding="utf-8") as infile, \
                    open(output_file, "w", encoding="utf-8", newline="") as outfile:

                reader = csv.DictReader(infile)
                if reader.fieldnames is None:
                    fieldnames = []
                else:
                    fieldnames = list(reader.fieldnames).copy()

                if additional_fields:
                    fieldnames.extend(additional_fields)

                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                yield reader, writer

        except Exception as e:
            logger.error(f"CSVファイル操作エラー: {str(e)}")
            raise e
