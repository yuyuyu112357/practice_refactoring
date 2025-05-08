from __future__ import annotations

import csv
import datetime
import re
from collections import defaultdict
from pathlib import Path
from typing import Protocol, IO, NamedTuple, Iterable

import matplotlib.pyplot as plt
from six import StringIO

# [リファクタリングの目標]
# 単一責任の原則(SRP) - 各機能を適切なクラスや関数に分割
# テスト容易性 - 依存関係の注入やモック可能な設計
# エラーハンドリング - 堅牢なエラー処理
# 設定の分離 - コードからハードコードされた設定を分離
# パフォーマンス最適化 - データ処理の効率化


# ログファイルの場所と出力先
LOG_DIR = Path("logs")
OUTPUT_DIR = Path("reports")


class DataSource(Protocol):
    def open_stream(self) -> IO[str]: ...


class FileDataSource:

    def __init__(self, filename: Path) -> None:
        self._file_path = filename

    def open_stream(self) -> IO[str]:
        return open(self._file_path, "r")


class InMemoryDataSource:

    def __init__(self, content: str) -> None:
        self._content = content

    def open_stream(self) -> IO[str]:
        return StringIO(self._content)


class LogAnalyzer:

    def __init__(self, data_source: DataSource) -> None:
        self._data_source = data_source

    def analyze(self, counters: Iterable[Countable]) -> None:
        with self._data_source.open_stream() as stream:
            for line in stream:
                for counter in counters:
                    counter.countup_if_match(line)


class Counters(NamedTuple):
    ip_counter: IpCounter
    status_counter: StatusCounter
    hourly_traffic_counter: HourlyTrafficCounter
    total_bytes_counter: TotalBytesCounter
    request_type_counter: RequestTypeCounter


class Countable(Protocol):
    def countup_if_match(self, line: str) -> None: ...


class IpCounter:
    IP_PATTERN = r"(\d+\.\d+\.\d+\.\d+)"

    def __init__(self) -> None:
        self._counts = defaultdict(int)

    def __len__(self) -> int:
        return len(self._counts)

    @property
    def total_requests(self) -> int:
        return sum(self._counts.values())

    def countup_if_match(self, line: str) -> None:
        match = re.search(self.IP_PATTERN, line)
        if match:
            ip = match.group(1)
            self._counts[ip] += 1

    def write(self, filename: Path) -> None:
        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["IPアドレス", "アクセス数"])
            for ip, count in sorted(self._counts.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([ip, count])


class StatusCounter:
    STATUS_PATTERN = r" (\d{3}) "

    def __init__(self) -> None:
        self._counts = defaultdict(int)

    @property
    def errors(self) -> int:
        return sum(count for status, count in self._counts.items() if status.startswith("5"))

    def countup_if_match(self, line: str) -> None:
        match = re.search(self.STATUS_PATTERN, line)
        if match:
            status = match.group(1)
            self._counts[status] += 1

    def write(self, filename: Path) -> None:
        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["ステータスコード", "回数"])
            for status, count in self._counts.items():
                writer.writerow([status, count])


class HourlyTrafficCounter:
    TIMESTAMP_PATTERN = r"\[(.+?)\]"

    def __init__(self, errors: list[str]) -> None:
        self._counts = defaultdict(int)
        self._errors = errors

    def countup_if_match(self, line: str) -> None:
        match = re.search(self.TIMESTAMP_PATTERN, line)
        if match:
            time_str = match.group(1)
            try:
                log_time = datetime.datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
                hour = log_time.hour
                self._counts[hour] += 1
            except ValueError:
                self._errors.append(f"無効なタイムスタンプ: {time_str}")

    def plot(self, axes: plt.Axes) -> None:
        hours = sorted(self._counts.keys())
        counts = [self._counts[hour] for hour in hours]
        axes.bar(hours, counts)
        axes.set_xlabel("時間帯")
        axes.set_ylabel("アクセス数")
        axes.set_title("時間帯別アクセス数")


class TotalBytesCounter:
    BYTES_PATTERN = r" (\d+)$"

    def __init__(self, errors: list[str]) -> None:
        self._total_bytes = 0
        self._errors = errors

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    def countup_if_match(self, line: str) -> None:
        match = re.search(self.BYTES_PATTERN, line)
        if match:
            try:
                bytes_sent = int(match.group(1))
                self._total_bytes += bytes_sent
            except ValueError:
                self._errors.append(f"無効なバイト数: {match.group(1)}")


class RequestTypeCounter:
    REQUEST_PATTERN = r'"([^"]*)"'

    def __init__(self) -> None:
        self._counts = defaultdict(int)

    def countup_if_match(self, line: str) -> None:
        match = re.search(self.REQUEST_PATTERN, line)
        if match:
            request = match.group(1)
            method = request.split()[0] if len(request.split()) > 0 else "UNKNOWN"
            self._counts[method] += 1

    def plot(self, axes: plt.Axes) -> None:
        methods = list(self._counts.keys())
        method_counts = [self._counts[method] for method in methods]
        axes.pie(method_counts, labels=methods, autopct="%1.1f%%")
        axes.set_title("HTTPメソッド分布")


class Report(Protocol):
    def write(self, filename: Path) -> None: ...


class IpReport:

    def __init__(self, ip_counter: IpCounter, errors: list[str]) -> None:
        self._ip_counter = ip_counter
        self._errors = errors

    def write(self, filename: Path) -> None:
        try:
            self._ip_counter.write(filename)
        except Exception as e:
            # 厳密には元の仕様と異なる
            self._errors.append(f"CSVファイル生成エラー: {str(e)}")


class StatusReport:

    def __init__(self, status_counter: StatusCounter, errors: list[str]) -> None:
        self._status_counter = status_counter
        self._errors = errors

    def write(self, filename: Path) -> None:
        try:
            self._status_counter.write(filename)
        except Exception as e:
            # 厳密には元の仕様と異なる
            self._errors.append(f"CSVファイル生成エラー: {str(e)}")


class TrafficReport:

    def __init__(
            self,
            hourly_traffic_counter: HourlyTrafficCounter,
            request_type_counter: RequestTypeCounter,
            errors: list[str],
    ) -> None:
        self._hourly_traffic_counter = hourly_traffic_counter
        self._request_type_counter = request_type_counter
        self._errors = errors

    def write(self, filename: Path) -> None:
        try:
            # 時間帯別トラフィック
            figure = plt.figure(figsize=(12, 6))
            axes = figure.add_subplot(1, 2, 1)
            self._hourly_traffic_counter.plot(axes)

            # リクエストタイプ分布
            plt.subplot(1, 2, 2)
            self._request_type_counter.plot(axes)

            figure.tight_layout()
            figure.savefig(filename)
        except Exception as e:
            self._errors.append(f"グラフ生成エラー: {str(e)}")


class SummaryReport:

    def __init__(
            self,
            ip_counter: IpCounter,
            status_counter: StatusCounter,
            total_bytes_counter: TotalBytesCounter,
            errors: list[str],
            date: str,
    ) -> None:
        self._ip_counter = ip_counter
        self._status_counter = status_counter
        self._total_bytes_counter = total_bytes_counter
        self._errors = errors
        self._date = date

    def write(self, filename: Path) -> None:
        total_requests = self._ip_counter.total_requests
        error_rate = self._status_counter.errors / total_requests if total_requests > 0 else 0

        with open(filename, "w") as file:
            file.write(f"ログ分析サマリー - {self._date}\n")
            file.write("=" * 50 + "\n\n")
            file.write(f"総リクエスト数: {total_requests}\n")
            file.write(f"総転送バイト量: {self._total_bytes_counter.total_bytes} バイト\n")
            file.write(f"ユニークIPアドレス数: {len(self._ip_counter)}\n")
            file.write(f"サーバーエラー率: {error_rate * 100:.2f}%\n\n")

            if self._errors:
                file.write("\nエラーログ:\n")
                for error in self._errors:
                    file.write(f"  {error}\n")


class ReportFactory(Protocol):
    def create_filename(self) -> Path: ...

    def create_report(self) -> Report: ...


class IpReportFactory:

    def __init__(self, counters: Counters, errors: list[str], date: str) -> None:
        self._counters = counters
        self._errors = errors
        self._date = date

    def create_filename(self) -> Path:
        return OUTPUT_DIR / f"ip_report_{self._date}.csv"

    def create_report(self) -> Report:
        return IpReport(self._counters.ip_counter, self._errors)


class StatusReportFactory:

    def __init__(self, counters: Counters, errors: list[str], date: str) -> None:
        self._counters = counters
        self._errors = errors
        self._date = date

    def create_filename(self) -> Path:
        return OUTPUT_DIR / f"status_report_{self._date}.csv"

    def create_report(self) -> Report:
        return StatusReport(self._counters.status_counter, self._errors)


class TrafficReportFactory:

    def __init__(self, counters: Counters, errors: list[str], date: str) -> None:
        self._counters = counters
        self._errors = errors
        self._date = date

    def create_filename(self) -> Path:
        return OUTPUT_DIR / f"traffic_report_{self._date}.png"

    def create_report(self) -> Report:
        return TrafficReport(
            self._counters.hourly_traffic_counter,
            self._counters.request_type_counter,
            self._errors,
        )


class SummaryReportFactory:

    def __init__(self, counters: Counters, errors: list[str], date: str) -> None:
        self._counters = counters
        self._errors = errors
        self._date = date

    def create_filename(self) -> Path:
        return OUTPUT_DIR / f"summary_report_{self._date}.txt"

    def create_report(self) -> Report:
        return SummaryReport(
            self._counters.ip_counter,
            self._counters.status_counter,
            self._counters.total_bytes_counter,
            self._errors,
            self._date,
        )


def analyze_logs(counters: Counters, errors: list[str]) -> None:
    filenames = [filename for filename in LOG_DIR.iterdir() if filename.suffix == ".log"]
    for filename in filenames:
        print(f"ファイル処理中: {filename}")

        try:
            data_source = FileDataSource(filename)
            log_analyzer = LogAnalyzer(data_source)
            log_analyzer.analyze(counters)
        except Exception as e:
            errors.append(f"ファイル処理エラー {filename}: {str(e)}")


def create_report(factory: ReportFactory) -> None:
    filename = factory.create_filename()
    report = factory.create_report()
    report.write(filename)


def main() -> None:
    # 出力ディレクトリがなければ作成
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 今日の日付を取得
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    errors = []
    counters = Counters(
        IpCounter(),
        StatusCounter(),
        HourlyTrafficCounter(errors),
        TotalBytesCounter(errors),
        RequestTypeCounter(),
    )

    print(f"ログ分析を開始します...")

    # ログファイルを処理
    analyze_logs(counters, errors)

    factories = [
        IpReportFactory(counters, errors, today),
        StatusReportFactory(counters, errors, today),
        TrafficReportFactory(counters, errors, today),
        SummaryReportFactory(counters, errors, today),
    ]

    # レポートを生成
    for factory in factories:
        create_report(factory)

    print(f"分析完了。レポートは {OUTPUT_DIR} ディレクトリに保存されました。")


if __name__ == "__main__":
    main()
