import csv
import datetime
import os
import re
from collections import defaultdict

import matplotlib.pyplot as plt

# [リファクタリングの目標]
# 単一責任の原則(SRP) - 各機能を適切なクラスや関数に分割
# テスト容易性 - 依存関係の注入やモック可能な設計
# エラーハンドリング - 堅牢なエラー処理
# 設定の分離 - コードからハードコードされた設定を分離
# パフォーマンス最適化 - データ処理の効率化


# ログファイルの場所と出力先
LOG_DIR = "logs"
OUTPUT_DIR = "reports"
# 分析対象のパターン
IP_PATTERN = r'(\d+\.\d+\.\d+\.\d+)'
TIMESTAMP_PATTERN = r'\[(.+?)\]'
REQUEST_PATTERN = r'"([^"]*)"'
STATUS_PATTERN = r' (\d{3}) '
BYTES_PATTERN = r' (\d+)$'


def analyze_logs():
    # 出力ディレクトリがなければ作成
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 今日の日付を取得
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # データ収集用の変数
    ip_counts = defaultdict(int)
    status_counts = defaultdict(int)
    hourly_traffic = defaultdict(int)
    total_bytes = 0
    request_types = defaultdict(int)
    errors = []

    print(f"ログ分析を開始します...")

    # ログファイルを処理
    for filename in os.listdir(LOG_DIR):
        if not filename.endswith('.log'):
            continue

        file_path = os.path.join(LOG_DIR, filename)
        print(f"ファイル処理中: {file_path}")

        try:
            with open(file_path, 'r') as file:
                for line in file:
                    # IPアドレスを抽出
                    ip_match = re.search(IP_PATTERN, line)
                    if ip_match:
                        ip = ip_match.group(1)
                        ip_counts[ip] += 1

                    # タイムスタンプを抽出
                    timestamp_match = re.search(TIMESTAMP_PATTERN, line)
                    if timestamp_match:
                        time_str = timestamp_match.group(1)
                        try:
                            log_time = datetime.datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
                            hour = log_time.hour
                            hourly_traffic[hour] += 1
                        except ValueError:
                            errors.append(f"無効なタイムスタンプ: {time_str}")

                    # ステータスコードを抽出
                    status_match = re.search(STATUS_PATTERN, line)
                    if status_match:
                        status = status_match.group(1)
                        status_counts[status] += 1

                    # 転送バイト数を抽出
                    bytes_match = re.search(BYTES_PATTERN, line)
                    if bytes_match:
                        try:
                            bytes_sent = int(bytes_match.group(1))
                            total_bytes += bytes_sent
                        except ValueError:
                            errors.append(f"無効なバイト数: {bytes_match.group(1)}")

                    # リクエストタイプを抽出
                    request_match = re.search(REQUEST_PATTERN, line)
                    if request_match:
                        request = request_match.group(1)
                        method = request.split()[0] if len(request.split()) > 0 else "UNKNOWN"
                        request_types[method] += 1
        except Exception as e:
            errors.append(f"ファイル処理エラー {file_path}: {str(e)}")

    # CSVレポートを生成
    try:
        with open(os.path.join(OUTPUT_DIR, f"ip_report_{today}.csv"), 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['IPアドレス', 'アクセス数'])
            for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([ip, count])

        with open(os.path.join(OUTPUT_DIR, f"status_report_{today}.csv"), 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['ステータスコード', '回数'])
            for status, count in status_counts.items():
                writer.writerow([status, count])
    except Exception as e:
        errors.append(f"CSVファイル生成エラー: {str(e)}")

    # グラフを作成
    try:
        plt.figure(figsize=(12, 6))

        # 時間帯別トラフィック
        plt.subplot(1, 2, 1)
        hours = sorted(hourly_traffic.keys())
        counts = [hourly_traffic[hour] for hour in hours]
        plt.bar(hours, counts)
        plt.xlabel('時間帯')
        plt.ylabel('アクセス数')
        plt.title('時間帯別アクセス数')

        # リクエストタイプ分布
        plt.subplot(1, 2, 2)
        methods = list(request_types.keys())
        method_counts = [request_types[method] for method in methods]
        plt.pie(method_counts, labels=methods, autopct='%1.1f%%')
        plt.title('HTTPメソッド分布')

        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f"traffic_report_{today}.png"))
    except Exception as e:
        errors.append(f"グラフ生成エラー: {str(e)}")

    # 集計レポート
    total_requests = sum(ip_counts.values())
    error_rate = sum(count for status, count in status_counts.items() if
                     status.startswith('5')) / total_requests if total_requests > 0 else 0

    with open(os.path.join(OUTPUT_DIR, f"summary_report_{today}.txt"), 'w') as file:
        file.write(f"ログ分析サマリー - {today}\n")
        file.write("=" * 50 + "\n\n")
        file.write(f"総リクエスト数: {total_requests}\n")
        file.write(f"総転送バイト量: {total_bytes} バイト\n")
        file.write(f"ユニークIPアドレス数: {len(ip_counts)}\n")
        file.write(f"サーバーエラー率: {error_rate * 100:.2f}%\n\n")

        file.write("最もアクセスの多いIPアドレス:\n")
        for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            file.write(f"  {ip}: {count}回\n")

        if errors:
            file.write("\nエラーログ:\n")
            for error in errors:
                file.write(f"  {error}\n")

    print(f"分析完了。レポートは {OUTPUT_DIR} ディレクトリに保存されました。")


if __name__ == "__main__":
    analyze_logs()
