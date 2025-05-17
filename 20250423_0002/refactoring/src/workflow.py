# グローバル変数
from __future__ import annotations

import logging
from pathlib import Path

from config import Config
from database import DatabaseManager
from file_manager import CsvHandler, FileManager
from processor import Stats, InputData, DataProcessor, process_data_event_context

logger = logging.getLogger(__name__)


class ProcessDataWorkflow:

    def __init__(
            self,
            config: Config,
            csv_handler: CsvHandler,
            file_manager: FileManager,
            db_manger: DatabaseManager,
    ) -> None:
        self._config = config
        self._csv_handler = csv_handler
        self._file_manager = file_manager
        self._db_manger = db_manger

    def process_data(self, input_file: Path) -> Stats:
        filename = input_file.name
        logger.info(f"ファイル処理開始: {filename}")

        output_file = self._file_manager.get_output_path(input_file)

        # 統計情報の初期化
        stats = Stats()
        processor = DataProcessor(stats)

        try:
            with self._csv_handler.open_csv_file(
                    input_file=input_file,
                    output_file=output_file,
                    additional_fields=["analysis_result", "confidence", "processed_timestamp"],
            ) as file_handlers:
                reader, writer = file_handlers
                for row in reader:
                    with process_data_event_context(stats):
                        data = InputData(**row)
                        result = processor.process(data)
                        writer.writerow(data.as_dict() | result.as_dict())

            # 処理が成功したらファイルをアーカイブ
            self._file_manager.move_to_archive(input_file)

        except Exception as e:
            # エラー発生時はエラーディレクトリに移動
            self._file_manager.move_to_error(input_file)
            logger.error(f"ファイル処理エラー: {filename} - {str(e)}")

        return stats

    def write_database(self, input_file: Path, stats: Stats, process_time: float) -> None:
        with self._db_manger:
            self._db_manger.insert_result(input_file, stats, process_time)

        logger.info(
            f"ファイル処理完了: {input_file.name} - レコード数: {stats.records}, "
            f"成功: {stats.success}, "
            f"エラー: {stats.errors}, "
            f"処理時間: {process_time:.2f}秒"
        )
