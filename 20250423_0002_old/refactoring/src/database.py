from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .processor import Stats

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
                stats.records.value,
                stats.success.value,
                stats.errors.value,
                process_time,
                datetime.now().isoformat(),
            )
        )
        self._connection.commit()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
