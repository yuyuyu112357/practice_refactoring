import csv
import logging
import random
import time
from datetime import datetime
from typing import Protocol

# ログ初期化
logger = logging.Logger("Log")


class Counter(Protocol):
    @property
    def value(self) -> int: ...

    def increment(self) -> None: ...


class RecordCounter:

    def __init__(self) -> None:
        self._count = 0

    def __str__(self) -> str:
        return f"{self._count}"

    @property
    def value(self) -> int:
        return self._count

    def increment(self) -> None:
        self._count += 1
        if self._count % 10 == 0:
            print(f"処理中... {self._count} レコード完了")


class SuccessCounter:

    def __init__(self) -> None:
        self._count = 0

    def __str__(self) -> str:
        return f"{self._count}"

    @property
    def value(self) -> int:
        return self._count

    def increment(self) -> None:
        self._count += 1


class ErrorCounter:

    def __init__(self) -> None:
        self._count = 0

    def __str__(self) -> str:
        return f"{self._count}"

    @property
    def value(self) -> int:
        return self._count

    def increment(self) -> None:
        self._count += 1


class Stats:

    def __init__(self) -> None:
        self._records = RecordCounter()
        self._success = SuccessCounter()
        self._errors = ErrorCounter()

    @property
    def records(self) -> RecordCounter:
        return self._records

    @property
    def success(self) -> SuccessCounter:
        return self._success

    @property
    def errors(self) -> ErrorCounter:
        return self._errors

    @property
    def error_rate(self) -> float:
        if self._records.value == 0:
            return 0.0
        return self._errors.value / self._records.value


class DataProcessor:
    PROCESS_DELAY = 0.1  # 処理遅延をシミュレート

    def __init__(self, writer: csv.DictWriter, stats: Stats) -> None:
        self._writer = writer
        self._stats = stats
        self._logger = logger

    def process(self, row: dict[str, str]) -> None:
        self._stats.records.increment()
        time.sleep(self.PROCESS_DELAY)  # 処理時間をシミュレート

        try:
            # 複雑な処理をシミュレート
            if random.random() < 0.05:  # 5%の確率でエラー
                raise ValueError(f"データ解析エラー: レコード {self._stats.records}")

            # 処理ロジック（実際はもっと複雑）
            analysis_result = self._calculate_analysis_result(row)
            confidence = random.uniform(0.7, 0.99)

            # 結果をCSVに書き込み
            row["analysis_result"] = analysis_result
            row["confidence"] = f"{confidence:.2f}"
            row["processed_timestamp"] = datetime.now().isoformat()
            self._writer.writerow(row)

            self._stats.success.increment()

        except Exception as e:
            self._stats.errors.increment()
            self._logger.error(f"レコード処理エラー: {str(e)}")

            # エラーが多すぎる場合は処理中断
            if self._stats.error_rate > 0.2:  # 20%以上がエラーの場合
                raise RuntimeError(f"エラー率が高すぎます: {self._stats.errors}/{self._stats.records}")

    # 分析結果計算（実際は複雑なビジネスロジック）
    def _calculate_analysis_result(self, data: dict[str, str]) -> float | str:
        # 複雑な計算をシミュレート
        time.sleep(self.PROCESS_DELAY)

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
