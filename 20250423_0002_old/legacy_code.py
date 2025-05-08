#!/usr/bin/env python3
# データ処理バッチ - 社内で長年使われてきた分析ツール

import os
import sys
import time
import csv
import json
import sqlite3
import random
import shutil
from datetime import datetime

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
DEBUG = False
PROCESS_DELAY = 0.1  # 処理遅延をシミュレート
DB_FILE = "analysis_results.db"
CONFIG = {
    "input_dir": "data/input",
    "output_dir": "data/output",
    "archive_dir": "data/archive",
    "error_dir": "data/errors",
    "log_file": "processor.log",
    "max_retry": 3,
    "batch_size": 100,
}


# データベース初期化
def init_db():
    print("データベースを初期化中...")
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()


# ログ出力関数
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONFIG["log_file"], "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    if DEBUG:
        print(f"[{timestamp}] {message}")


# ディレクトリ作成
def create_directories():
    for dir_name in ["input_dir", "output_dir", "archive_dir", "error_dir"]:
        dir_path = CONFIG[dir_name]
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            log_message(f"ディレクトリを作成しました: {dir_path}")


# データファイル処理関数
def process_data_file(filename):
    log_message(f"ファイル処理開始: {filename}")
    start_time = time.time()

    input_path = os.path.join(CONFIG["input_dir"], filename)
    output_path = os.path.join(CONFIG["output_dir"], f"processed_{filename}")
    archive_path = os.path.join(CONFIG["archive_dir"], filename)
    error_path = os.path.join(CONFIG["error_dir"], filename)

    # 統計情報の初期化
    stats = {
        "records": 0,
        "success": 0,
        "errors": 0,
    }

    try:
        # CSVファイルを読み込み、処理して結果を出力
        with open(input_path, "r", encoding="utf-8") as infile, \
                open(output_path, "w", encoding="utf-8", newline="") as outfile:

            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ["analysis_result", "confidence", "processed_timestamp"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                stats["records"] += 1
                time.sleep(PROCESS_DELAY)  # 処理時間をシミュレート

                try:
                    # 複雑な処理をシミュレート
                    if random.random() < 0.05:  # 5%の確率でエラー
                        raise ValueError(f"データ解析エラー: レコード {stats['records']}")

                    # 処理ロジック（実際はもっと複雑）
                    analysis_result = calculate_analysis_result(row)
                    confidence = random.uniform(0.7, 0.99)

                    # 結果をCSVに書き込み
                    row["analysis_result"] = analysis_result
                    row["confidence"] = f"{confidence:.2f}"
                    row["processed_timestamp"] = datetime.now().isoformat()
                    writer.writerow(row)

                    stats["success"] += 1

                    # 進捗表示（大量データの場合に役立つ）
                    if stats["records"] % 10 == 0:
                        print(f"処理中... {stats['records']} レコード完了")

                except Exception as e:
                    stats["errors"] += 1
                    log_message(f"レコード処理エラー: {str(e)}")
                    # エラーが多すぎる場合は処理中断
                    if stats["errors"] > stats["records"] * 0.2:  # 20%以上がエラーの場合
                        raise RuntimeError(f"エラー率が高すぎます: {stats['errors']}/{stats['records']}")

        # 処理が成功したらファイルをアーカイブ
        shutil.move(input_path, archive_path)
        log_message(f"ファイルを処理してアーカイブしました: {filename}")

    except Exception as e:
        # エラー発生時はエラーディレクトリに移動
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.move(input_path, error_path)
        log_message(f"ファイル処理エラー: {filename} - {str(e)}")

    process_time = time.time() - start_time

    # 処理結果をデータベースに記録
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO results (filename, records, success, errors, process_time, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (filename, stats["records"], stats["success"], stats["errors"], process_time, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    log_message(
        f"ファイル処理完了: {filename} - レコード数: {stats['records']}, 成功: {stats['success']}, エラー: {stats['errors']}, 処理時間: {process_time:.2f}秒")
    return stats


# 分析結果計算（実際は複雑なビジネスロジック）
def calculate_analysis_result(data):
    # 複雑な計算をシミュレート
    time.sleep(PROCESS_DELAY)

    # 適当な計算ロジック（実際はもっと複雑）
    try:
        value1 = float(data.get("value1", 0))
        value2 = float(data.get("value2", 0))
        category = data.get("category", "").lower()

        if category == "a":
            result = value1 * 1.5 + value2 * 0.5
        elif category == "b":
            result = value1 + value2 * 2
        elif category == "c":
            result = (value1 + value2) / 2 * 3
        else:
            result = value1 + value2

        return round(result, 2)
    except:
        return "ERROR"


# サマリーレポート生成
def generate_summary_report():
    log_message("サマリーレポート生成開始")

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
    report_path = os.path.join(CONFIG["output_dir"], f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    log_message(f"サマリーレポート生成完了: {report_path}")
    print("\n===== 処理サマリー =====")
    print(f"処理ファイル数: {summary['total_files']}")
    print(f"総レコード数: {summary['total_records']}")
    print(f"成功レコード: {summary['successful_records']}")
    print(f"エラーレコード: {summary['error_records']}")
    print(f"成功率: {summary['success_rate']:.2f}%")
    print(f"平均処理時間: {summary['average_process_time']:.2f}秒")
    print("========================\n")


# メイン処理ループ
def main():
    global DEBUG

    # コマンドライン引数の処理
    if len(sys.argv) > 1:
        if "--debug" in sys.argv:
            DEBUG = True
            print("デバッグモードが有効です")
        if "--help" in sys.argv:
            print("使用方法: ./legacy_data_processor.py [オプション]")
            print("オプション:")
            print("  --debug    デバッグモードを有効にする")
            print("  --help     このヘルプを表示")
            return

    print("=== データ処理バッチ開始 ===")
    start_time = time.time()

    # 初期化
    if not os.path.exists(CONFIG["log_file"]):
        with open(CONFIG["log_file"], "w") as f:
            f.write("")

    log_message("処理を開始します")
    create_directories()
    init_db()

    # 入力ディレクトリのファイルを処理
    input_files = [f for f in os.listdir(CONFIG["input_dir"]) if f.endswith(".csv")]
    if not input_files:
        log_message("処理対象のCSVファイルがありません")
        print("処理対象のCSVファイルがありません。data/inputディレクトリにCSVファイルを配置してください。")
        return

    log_message(f"処理対象ファイル数: {len(input_files)}")
    print(f"処理対象ファイル数: {len(input_files)}")

    total_stats = {
        "files": len(input_files),
        "records": 0,
        "success": 0,
        "errors": 0,
    }

    # 各ファイルを処理
    for i, filename in enumerate(input_files, 1):
        print(f"\nファイル {i}/{len(input_files)} 処理中: {filename}")
        stats = process_data_file(filename)

        # 全体の統計を更新
        total_stats["records"] += stats["records"]
        total_stats["success"] += stats["success"]
        total_stats["errors"] += stats["errors"]

    # サマリーを生成
    generate_summary_report()

    # 終了処理
    total_time = time.time() - start_time
    log_message(f"すべての処理が完了しました。総処理時間: {total_time:.2f}秒")
    print(f"\n全処理が完了しました。総処理時間: {total_time:.2f}秒")


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
