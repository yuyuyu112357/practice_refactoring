from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from processor import Stats

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Summary:
    total_files: int
    total_records: int
    successful_records: int
    error_records: int
    average_process_time: float
    generated_at: datetime

    @property
    def success_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return self.successful_records / self.total_records * 100

    @classmethod
    def create(
            cls,
            total_files: int,
            total_records: int | None,
            successful_records: int | None,
            error_records: int | None,
            average_process_time: float | None,
    ) -> Summary:
        return cls(
            total_files=total_files,
            total_records=total_records if total_records else 0,
            successful_records=successful_records if successful_records else 0,
            error_records=error_records if error_records else 0,
            average_process_time=average_process_time if average_process_time else 0,
            generated_at=datetime.now(),
        )


class DatabaseManager:

    def __init__(self, db_file: Path) -> None:
        self._db_file = db_file
        self._connection = None
        self._setup()

    def _setup(self) -> None:
        if self._db_file.exists():
            self._db_file.unlink()
        self._connection = sqlite3.connect(self._db_file)
        cursor = self._connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY,
                filename TEXT,
                records INTEGER,
                success INTEGER,
                errors INTEGER,
                process_time REAL,
                timestamp TEXT
            )
    ''')
        self._connection.commit()
        self.close()

    def __enter__(self) -> DatabaseManager:
        self._connection = sqlite3.connect(self._db_file)
        return self

    def insert_result(self, input_file_path: Path, stats: Stats, process_time: float) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            "INSERT INTO results (filename, records, success, errors, process_time, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                input_file_path,
                stats.records,
                stats.success,
                stats.errors,
                process_time,
                datetime.now().isoformat(),
            )
        )
        self._connection.commit()

    def get_summary(self) -> Summary:
        cursor = self._connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) as files, "
            "SUM(records) as records, "
            "SUM(success) as success, "
            "SUM(errors) as errors, "
            "AVG(process_time) as avg_time FROM results"
        )
        return Summary.create(*cursor.fetchall())

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
