#!/usr/bin/env python3
# データ処理バッチ - 社内で長年使われてきた分析ツール
import argparse
import logging
import os
import sys
import time
from pathlib import Path

from src.config import TomlConfig, Config
from src.database import DatabaseManager
from src.file_manager import FileManager, CsvHandler
from src.report import ReportGenerator
from src.util import BinaryFileDataSource, Timer
from src.workflow import ProcessDataWorkflow

DB_FILE = "analysis_results.db"


# リファクタリングの目標
# このレガシーコードを以下の目標でリファクタリングしてみましょう：
# 1.正常な終了処理 - プログラムが自動的に終了するようにする
# 2.責任の分離 - 単一責任の原則に従ってコードを整理
# 3.設定の外部化 - 設定を別ファイルに分離
# 4.コマンドパターンの実装 - 処理を独立したコマンドとして分離
# 5.エラーハンドリングの改善 - 例外処理を適切に実装
# 6.テスト容易性の向上 - 依存性注入などを活用
# 7.進捗状況の可視化 - 長時間実行時の進捗表示
# 8.リソース管理の改善 - コンテキストマネージャを活用
#
# リファクタリングのアプローチ
# モジュール分割
#   設定管理、データベース操作、ファイル処理、レポート生成など機能ごとにモジュール化
# クラス設計
#   DataProcessor, DatabaseManager, FileManager, ReportGenerator などのクラスを作成
# コマンドパターン
#   各処理を独立したコマンドオブジェクトとして実装
# オブザーバーパターン
#   処理の進捗を監視・表示するためのオブザーバーを実装
# コンフィグファイル
#   YAMLやJSONで設定を外部化


class ApplicationInitializer:

    def __init__(self) -> None:
        self._logger = self.setup_basic_logging()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @staticmethod
    def setup_basic_logging() -> logging.Logger:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            stream=sys.stdout
        )
        return logging.getLogger()

    @staticmethod
    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="データ処理ツール")
        parser.add_argument("--debug", action="store_true", help="デバッグモードを有効にする")
        return parser.parse_args()

    def get_config_path(self) -> Path:
        config_file_path = os.getenv("CONFIG_FILE_PATH")
        if not config_file_path:
            self._logger.error("CONFIG_FILE_PATH 環境変数が設定されていません")
            raise
        return Path(config_file_path)


class Application:

    def __init__(self, initializer: ApplicationInitializer) -> None:
        self._logger = initializer.logger
        self._args = initializer.parse_args()
        self._config_path = initializer.get_config_path()

    def run(self) -> None:
        self._logger.info("=== データ処理バッチ開始 ===")
        start_time = time.time()

        config = self._read_config(self._config_path)
        self._setup_detailed_logging(config, self._args.debug)

        self._logger.info("処理を開始します")
        file_manager = FileManager(config)
        file_manager.create_directories_if_not_exist()

        db_manger = DatabaseManager(Path(DB_FILE))
        self._process_data(config, file_manager, db_manger)

        report_path = file_manager.get_summary_report_path()
        self._generate_report(report_path, config, db_manger)

        total_time = time.time() - start_time
        self._logger.info(f"すべての処理が完了しました。総処理時間: {total_time:.2f}秒")

    @staticmethod
    def _read_config(config_path: Path) -> Config:
        data_source = BinaryFileDataSource(config_path)
        config_parser = TomlConfig(data_source)
        return config_parser.parse()

    @staticmethod
    def _setup_detailed_logging(config: Config, debug: bool) -> logging.Logger:
        # ロガーをリセット
        for handler in logging.root.handlers:
            logging.root.removeHandler(handler)

        # 新しい詳細な設定
        level = logging.DEBUG if debug else logging.INFO

        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=config.log_file,
            filemode="a"
        )

        # コンソール出力用のハンドラを追加
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

        logger = logging.getLogger()
        if debug:
            logger.info("デバッグモードが有効です")

        return logger

    def _process_data(
            self,
            config: Config,
            file_manager: FileManager,
            db_manger: DatabaseManager,
    ) -> None:
        # 入力ディレクトリのファイルを処理
        input_files = file_manager.list_input_files(pattern="*.csv")
        if not input_files:
            self._logger.error(
                "処理対象のCSVファイルがありません。"
                f"{config.input_dir}ディレクトリにCSVファイルを配置してください。"
            )
            raise
        self._logger.info(f"処理対象ファイル数: {len(input_files)}")

        # 各ファイルを処理
        csv_handler = CsvHandler()
        process_data_workflow = ProcessDataWorkflow(config, csv_handler, file_manager, db_manger)
        for i, input_file in enumerate(input_files, 1):
            self._logger.info(f"ファイル {i}/{len(input_files)} 処理中: {input_file.name}")

            with Timer() as t:
                stats = process_data_workflow.process_data(input_file)
            process_data_workflow.write_database(input_file, stats, t())

    @staticmethod
    def _generate_report(report_path: Path, config: Config, db_manger: DatabaseManager) -> None:
        # サマリーを生成
        report_generator = ReportGenerator(config, db_manger)
        report_generator.generate(report_path)


# メイン処理ループ
def main() -> None:
    initializer = ApplicationInitializer()
    app = Application(initializer)
    app.run()


# エントリーポイント
if __name__ == "__main__":
    os.environ["CONFIG_FILE_PATH"] = r"C:\work\tmp_study\20250423_0002\refactoring\config\default.toml"
    main()
