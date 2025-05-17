from __future__ import annotations

import logging
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Self, Generator

from util import BaseDispatcher

logger = logging.getLogger(__name__)


class Counter(int):

    def __new__(cls, x: int) -> Self:
        return super().__new__(cls, x)

    def increment(self) -> Self:
        return self.__class__(self + 1)


class Stats:

    def __init__(self) -> None:
        self._records = Counter(0)
        self._success = Counter(0)
        self._errors = Counter(0)

    @property
    def records(self) -> Counter:
        return self._records

    @property
    def success(self) -> Counter:
        return self._success

    @property
    def errors(self) -> Counter:
        return self._errors

    @property
    def error_rate(self) -> float:
        if self._records == 0:
            return 0.0
        return self._errors / self._records

    def increment_records(self) -> None:
        self._records = self._records.increment()

    def increment_success(self) -> None:
        self._success = self._success.increment()

    def increment_errors(self) -> None:
        self._errors = self._errors.increment()


@dataclass(frozen=True)
class BeforeContext:
    stats: Stats


@dataclass(frozen=True)
class AfterContext:
    stats: Stats


@dataclass(frozen=True)
class ErrorContext:
    stats: Stats
    exception: Exception


def on_before_process_listener(content: BeforeContext) -> None:
    content.stats.increment_records()


def on_after_process_listener(content: AfterContext) -> None:
    content.stats.increment_success()
    if content.stats.records % 10 == 0:
        logger.info(f"処理中... {content.stats.records} レコード完了")


def on_error_process_listener(content: ErrorContext) -> None:
    content.stats.increment_errors()
    logger.error(f"レコード処理エラー: {content.exception}")
    if content.stats.error_rate > 0.2:  # 20%以上がエラーの場合
        raise RuntimeError(f"エラー率が高すぎます: {content.stats.errors}/{content.stats.records}")


on_before_process = BaseDispatcher[BeforeContext]()
on_after_process = BaseDispatcher[AfterContext]()
on_error_process = BaseDispatcher[ErrorContext]()

on_before_process.subscribe(on_before_process_listener)
on_after_process.subscribe(on_after_process_listener)
on_error_process.subscribe(on_error_process_listener)


@contextmanager
def process_data_event_context(stats: Stats) -> Generator[None]:
    try:
        on_before_process.notify(BeforeContext(stats))
        yield
        on_after_process.notify(AfterContext(stats))
    except Exception as e:
        on_error_process.notify(ErrorContext(stats, e))
        raise


@dataclass(frozen=True)
class InputData:
    value1: float
    value2: float
    category: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Result:
    analysis_result: float | str
    confidence: float
    processed_timestamp: datetime

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


class DataProcessor:
    PROCESS_DELAY = 0.1

    def __init__(self, stats: Stats) -> None:
        self._stats = stats

    def process(self, data: InputData) -> Result:
        time.sleep(self.PROCESS_DELAY)  # 処理時間をシミュレート

        # 複雑な処理をシミュレート
        if random.random() < 0.05:  # 5%の確率でエラー
            raise ValueError(f"データ解析エラー: レコード {self._stats.records}")

        # 処理ロジック（実際はもっと複雑）
        analysis_result = self._calculate_analysis_result(data)
        confidence = random.uniform(0.7, 0.99)

        # 結果をCSVに書き込み
        return Result(
            analysis_result=analysis_result,
            confidence=confidence,
            processed_timestamp=datetime.now(),
        )

    # 分析結果計算（実際は複雑なビジネスロジック）
    def _calculate_analysis_result(self, data: InputData):
        # 複雑な計算をシミュレート
        time.sleep(self.PROCESS_DELAY)

        # 適当な計算ロジック（実際はもっと複雑）
        try:
            if data.category == "a":
                result = data.value1 * 1.5 + data.value2 * 0.5
            elif data.category == "b":
                result = data.value1 + data.value2 * 2
            elif data.category == "c":
                result = (data.value1 + data.value2) / 2 * 3
            else:
                result = data.value1 + data.value2

            return round(result, 2)
        except Exception:
            return "ERROR"
