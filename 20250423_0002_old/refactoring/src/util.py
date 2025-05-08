from io import StringIO, BytesIO
from pathlib import Path
from typing import Protocol, IO


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
