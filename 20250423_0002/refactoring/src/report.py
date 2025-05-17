import json
import logging
from pathlib import Path

from config import Config
from database import DatabaseManager

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager

    def generate(self, report_path: Path) -> None:
        logger.info("サマリーレポート生成開始")
        summary = self.db_manager.get_summary()

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"サマリーレポート生成完了: {report_path}")
        logger.info("===== 処理サマリー =====")
        logger.info(f"処理ファイル数: {summary.total_files}")
        logger.info(f"総レコード数: {summary.total_records}")
        logger.info(f"成功レコード: {summary.successful_records}")
        logger.info(f"エラーレコード: {summary.error_records}")
        logger.info(f"成功率: {summary.success_rate:.2f}%")
        logger.info(f"平均処理時間: {summary.average_process_time:.2f}秒")
        logger.info("========================")
