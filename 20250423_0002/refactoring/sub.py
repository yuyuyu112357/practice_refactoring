# グローバル変数
import csv
import json
import logging
import os
import random
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from src.config import Config

PROCESS_DELAY = 0.1  # 処理遅延をシミュレート

logger = logging.getLogger(__name__)


# データファイル処理関数
def process_data_file(config: Config, input_path: Path):
    start_time = time.time()
    filename = input_path.name
    logger.info(f"ファイル処理開始: {filename}")

    output_path = config.output_dir / f"processed_{filename}"
    archive_path = config.archive_dir / filename
    error_path = config.error_dir / filename

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
                        raise ValueError(f"データ解析エラー: レコード {stats["records"]}")

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
                        logger.info(f"処理中... {stats["records"]} レコード完了")

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"レコード処理エラー: {str(e)}")
                    # エラーが多すぎる場合は処理中断
                    if stats["errors"] > stats["records"] * 0.2:  # 20%以上がエラーの場合
                        raise RuntimeError(f"エラー率が高すぎます: {stats["errors"]}/{stats["records"]}")

        # 処理が成功したらファイルをアーカイブ
        shutil.move(input_path, archive_path)
        logger.info(f"ファイルを処理してアーカイブしました: {filename}")

    except Exception as e:
        # エラー発生時はエラーディレクトリに移動
        if output_path.exists():
            output_path.unlink()
        shutil.move(input_path, error_path)
        logger.error(f"ファイル処理エラー: {filename} - {str(e)}")

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

    logger.info(
        f"ファイル処理完了: {filename} - レコード数: {stats["records"]}, "
        f"成功: {stats["success"]}, "
        f"エラー: {stats["errors"]}, "
        f"処理時間: {process_time:.2f}秒"
    )
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
def generate_summary_report(config: Config) -> None:
    logger.info("サマリーレポート生成開始")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as files, "
        "SUM(records) as records, "
        "SUM(success) as success, "
        "SUM(errors) as errors, "
        "AVG(process_time) as avg_time FROM results"
    )
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
    report_path = config.output_dir / f"summary_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"サマリーレポート生成完了: {report_path}")
    print("\n===== 処理サマリー =====")
    print(f"処理ファイル数: {summary["total_files"]}")
    print(f"総レコード数: {summary["total_records"]}")
    print(f"成功レコード: {summary["successful_records"]}")
    print(f"エラーレコード: {summary["error_records"]}")
    print(f"成功率: {summary["success_rate"]:.2f}%")
    print(f"平均処理時間: {summary["average_process_time"]:.2f}秒")
    print("========================\n")
