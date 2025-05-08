#!/usr/bin/env python3
# データ処理バッチ - 社内で長年使われてきた分析ツール

import csv
import json
import logging
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .src.config import TomlConfig, Config
from .src.database import DatabaseManager
from .src.processor import Stats, DataProcessor
from .src.util import BinaryFileDataSource

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


# グローバル変数
DB_FILE = Path("analysis_results.db")
CONFIG_FILE_PATH = Path("./config/config.toml")

# ログ初期化
logger = logging.Logger("Log")


class LogSetupFactory(Protocol):
    @staticmethod
    def create_formatter() -> logging.Formatter: ...

    def set_handler(self, formatter: logging.Formatter) -> None: ...

    @staticmethod
    def set_level() -> None: ...


class NormalLogSetupFactory:

    def __init__(self, config: Config) -> None:
        self._config = config

    @staticmethod
    def create_formatter() -> logging.Formatter:
        return logging.Formatter(fmt="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    def set_handler(self, formatter: logging.Formatter) -> None:
        fh = logging.FileHandler(self._config.log_file, mode="a")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    @staticmethod
    def set_level() -> None:
        logger.setLevel(logging.INFO)


class DebugLogSetupFactory:

    def __init__(self, config: Config) -> None:
        self._config = config
        self._normal_logger_factory = NormalLogSetupFactory(config)

    @staticmethod
    def create_formatter() -> logging.Formatter:
        return logging.Formatter(fmt="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    def set_handler(self, formatter: logging.Formatter) -> None:
        self._normal_logger_factory.set_handler(formatter)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    @staticmethod
    def set_level() -> None:
        logger.setLevel(logging.DEBUG)


def create_log_setup_factory(config: Config, debug: bool) -> LogSetupFactory:
    if debug:
        return DebugLogSetupFactory(config)
    else:
        return NormalLogSetupFactory(config)


def setup_logger(factory: LogSetupFactory) -> None:
    formatter = factory.create_formatter()
    factory.set_handler(formatter)
    factory.set_level()


# データファイル処理関数
def process_data_file(config: Config, input_path: Path):
    output_path = config.output_dir / f"processed_{input_path.name}"
    archive_path = config.archive_dir / input_path.name
    error_path = config.archive_dir / input_path.name

    # 統計情報の初期化
    stats = Stats()

    try:
        # CSVファイルを読み込み、処理して結果を出力
        with open(input_path, "r", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ["analysis_result", "confidence", "processed_timestamp"]

        with open(output_path, "w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            processor = DataProcessor(writer, stats)
            for row in reader:
                processor.process(row)

        # 処理が成功したらファイルをアーカイブ
        shutil.move(input_path, archive_path)
        logger.info(f"ファイルを処理してアーカイブしました: {input_path}")

    except Exception as e:
        # エラー発生時はエラーディレクトリに移動
        if output_path.exists():
            output_path.unlink()
        shutil.move(input_path, error_path)
        logger.error(f"ファイル処理エラー: {input_path} - {str(e)}")

    return stats


# サマリーレポート生成
def generate_summary_report(config: Config) -> None:
    logger.info("サマリーレポート生成開始")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as files, SUM(records) as records, SUM(success) as success, SUM(errors) as errors, AVG(process_time) as avg_time FROM results")
    row = cursor.fetchone()

    summary = {
        "total_files": row[0],
        "total_records": row[1] if row[1] else 0,
        "successful_records": row[2] if row[2] else 0,
        "error_records": row[3] if row[3] else 0,
        "average_process_time": row[4] if row[4] else 0,
        "generated_at": datetime.now().isoformat()
    }

    # 成功率の計算
    if summary["total_records"] > 0:
        summary["success_rate"] = (summary["successful_records"] / summary["total_records"]) * 100
    else:
        summary["success_rate"] = 0

    conn.close()

    # JSONレポート出力
    report_path = config.output_dir / f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"サマリーレポート生成完了: {report_path}")
    print("\n===== 処理サマリー =====")
    print(f"処理ファイル数: {summary['total_files']}")
    print(f"総レコード数: {summary['total_records']}")
    print(f"成功レコード: {summary['successful_records']}")
    print(f"エラーレコード: {summary['error_records']}")
    print(f"成功率: {summary['success_rate']:.2f}%")
    print(f"平均処理時間: {summary['average_process_time']:.2f}秒")
    print("========================\n")


# メイン処理ループ
def main() -> None:
    debug = False

    # コマンドライン引数の処理
    if len(sys.argv) > 1:
        if "--debug" in sys.argv:
            debug = True
            print("デバッグモードが有効です")
        if "--help" in sys.argv:
            print("使用方法: ./legacy_data_processor.py [オプション]")
            print("オプション:")
            print("  --debug    デバッグモードを有効にする")
            print("  --help     このヘルプを表示")
            return

    print("=== データ処理バッチ開始 ===")
    start_time = time.time()

    # 設定ファイルの読み込み
    if not CONFIG_FILE_PATH.is_file():
        print(f"設定ファイルが見つかりません: {CONFIG_FILE_PATH}")
        return
    data_source = BinaryFileDataSource(CONFIG_FILE_PATH)
    config_parser = TomlConfig(data_source)
    config = config_parser.parse()

    # ログ設定
    log_setup_factory = create_log_setup_factory(config, debug)
    setup_logger(log_setup_factory)

    logger.info("処理を開始します")
    logger.info("データベースを初期化中...")
    db_manager = DatabaseManager(DB_FILE)

    # 入力ディレクトリのファイルを処理
    input_file_paths = [f for f in config.input_dir.iterdir() if f.suffix == ".csv"]
    if not input_file_paths:
        logger.error("処理対象のCSVファイルがありません。data/inputディレクトリにCSVファイルを配置してください。")
        return
    logger.info(f"処理対象ファイル数: {len(input_file_paths)}")

    # 各ファイルを処理
    for i, input_file_path in enumerate(input_file_paths, 1):
        logger.info(f"ファイル {i}/{len(input_file_paths)} 処理中: {input_file_path}")
        start_time = time.time()
        stats = process_data_file(config, input_file_path)
        process_time = time.time() - start_time

        # 処理結果をデータベースに記録
        with db_manager as db:
            db.insert_result(
                input_file_path,
                stats,
                process_time,
            )

        logger.info(
            f"ファイル処理完了: {input_file_path} - レコード数: {stats.records}, "
            f"成功: {stats.success}, "
            f"エラー: {stats.errors}, "
            f"処理時間: {process_time:.2f}秒"
        )

    # サマリーを生成
    generate_summary_report(config)

    # 終了処理
    total_time = time.time() - start_time
    logger.info(f"すべての処理が完了しました。総処理時間: {total_time:.2f}秒")


# エントリーポイント
if __name__ == "__main__":
    main()
    # ここではプログラムが終了しないシミュレーション
    print("\n処理は完了しましたが、バックグラウンドタスクが進行中です...")
    # 実際のレガシーコードでは、何らかの理由（無限ループ、ブロッキング処理など）で
    # プログラムが終了せず、手動でCtrl+Cなどで強制終了する必要がある
    while True:
        time.sleep(10)
        print("まだ実行中です... Ctrl+Cで終了してください")
