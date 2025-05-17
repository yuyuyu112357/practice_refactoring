import time
from contextlib import contextmanager
from io import StringIO, BytesIO
from pathlib import Path
from typing import Protocol, IO, Callable, Iterator


# テキスト読み込み
class TextDataSource(Protocol):
    def open_stream(self) -> IO[str]: ...


class TextFileDataSource:

    def __init__(self, filename: Path) -> None:
        self._file_path = filename

    def open_stream(self) -> IO[str]:
        return open(self._file_path, "r")


class TextInMemoryDataSource:

    def __init__(self, content: str) -> None:
        self._content = content

    def open_stream(self) -> IO[str]:
        return StringIO(self._content)


# バイナリデータ読み込み
class BinaryDataSource(Protocol):
    def open_stream(self) -> IO[bytes]: ...


class BinaryFileDataSource:

    def __init__(self, filename: Path) -> None:
        self._file_path = filename

    def open_stream(self) -> IO[bytes]:
        return open(self._file_path, "rb")


class BinaryInMemoryDataSource:

    def __init__(self, content: bytes) -> None:
        self._content = content

    def open_stream(self) -> IO[bytes]:
        return BytesIO(self._content)


class BaseDispatcher[T]:

    def __init__(self) -> None:
        self._listeners: list[Callable[[T], None]] = []

    def subscribe(self, listener: Callable[[T], None]) -> None:
        self._listeners.append(listener)

    def notify(self, payload: T) -> None:
        for listener in self._listeners:
            listener(payload)


@contextmanager
def calculate_processing_time() -> Iterator[Callable[[], float]]:
    start_time = time.time()

    def get_process_time() -> float:
        return time.time() - start_time

    yield get_process_time


class Timer:
    _start: float
    _end: float | None

    def __enter__(self) -> Callable[[], float]:
        self._start = time.time()
        self._end = None
        return self.elapsed

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._end = time.time()

    def elapsed(self) -> float:
        return (self._end or time.time()) - self._start
