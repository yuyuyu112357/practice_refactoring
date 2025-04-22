from __future__ import annotations

import csv
from dataclasses import dataclass


# [課題]
# 以下は、あまり保守しやすくない例のレガシーコードです。グローバル変数の使用や、複数の責務が1つの関数にまとめられているなど、
# さまざまな問題があります。このコードを題材に、リファクタリングに取り組んでみてください。

# ■ リファクタリング時に着目したいポイント:
# グローバル変数の使用を減らす、もしくはやめる。
#   -> グローバル変数を使わないようにする。
# I/O 処理と集計処理を分離し、関数を小さく保ち、責務を明確化する。
#   -> I/O 処理と集計処理を分離する。
# エラー処理を整理し、不備のある行に対してどのように対応するか検討する。
#   -> 0埋めする
# 再利用しやすいようにクラス化または関数分割を検討する。
#   -> クラス化する。
# リファクタリングした結果、可読性と保守性が上がったかどうかを確認する。
#   -> 確認する。

# [添削]
# 以下の点で、大きく改善・整理されていて非常に良いリファクタリングになっていると思います。
#
# • グローバル変数をやめ、全てクラスや関数のスコープ内で処理することで、データの扱いが明確になりました。
# • データ取得(読み込み)と集計処理を分割することで、責務が明確化され、保守性·可読性が向上しています。
# • Data という小さなデータ構造(DataClass)を導入し、それをリストで扱う DataList クラスにすることで、
#   手続き的なコードよりもオブジェクト指向的で拡張しやすい構造になっています。
# • avg_total() を計算するときに、0件時のエラー回避(例: ゼロ除算)を行うなどの検討が必要ですが、
#   例外的状況に対して明示的な対処をしている点(raise ValueError)は好ましいです。
#
# 以下、さらに改善できそうな項目をいくつか挙げます。
#
# CSVReader の例外処理をもう少し細かく行う
#   数値変換に失敗する行が混在する可能性があります。現状では int(v.strip()) で
#   ValueError が起きた場合にdata_listへの追加前に例外が発生するため、途中で処理が停止してしまいます。
#   「変換できなかったら None にする」「例外としてログを出力してスキップする」など、
#   方針を検討してみると現場レベルで使いやすいコードになるでしょう。
#
# 列数が3列より多い・少ない場合の扱いを定義する
#   今回の例だと Data クラスは3列を想定していますが、CSV（現場では4列以上だったり2列だったり）を想定すると
#   「余分な列は無視」または「足りないカラムは None とする」など、仕様を明示して実装するとさらに保守しやすくなります。
#    たとえば、「列数が3列未満の場合は Data(val_a, val_b, None) のように補う」「4列以上の場合は一旦無視する」など設計が考えられます。
#
# 平均の計算時に、要素数が0のときの対応
#   constructor で raise ValueError をしていますが、実際にはファイルの中身が空行やヘッダのみのケースを含む場合もあるかもしれません。
#   データが0件の場合、avg_total() で ZeroDivisionError が起きないようにガードを入れる、
#   あるいは CSVReader の段階でエラーを出す、などの選択肢があります。
#
# パスの取り扱いを柔軟にする
#   main 関数内で data_file_path を指定しているのも、今の段階ではわかりやすくて良いですが、
#   将来的にコマンドライン引数や設定ファイルなどからパスを受け取りたい要望が出る場合は、柔軟に処理できるようにしておくと拡張性が高まります。


@dataclass(frozen=True)
class Data:
    val_a: int | None = None
    val_b: int | None = None
    val_c: int | None = None

    @property
    def total(self, *, fill_value: int = 0) -> int:
        val_a = self.val_a or fill_value
        val_b = self.val_b or fill_value
        val_c = self.val_c or fill_value
        return val_a + val_b + val_c

    def fill_none(self, *, fill_value: int = 0) -> Data:
        val_a = self.val_a or fill_value
        val_b = self.val_b or fill_value
        val_c = self.val_c or fill_value
        return Data(val_a, val_b, val_c)


class DataList:

    def __init__(self, *, data_list: list[Data] | None = None) -> None:
        self._data_list = data_list or []

    def __len__(self) -> int:
        return len(self._data_list)

    def append(self, data: Data) -> None:
        self._data_list.append(data)

    def sum_total(self) -> int:
        return sum(data.total for data in self._data_list)

    def avg_total(self) -> float:
        if len(self._data_list) == 0:
            return 0.0
        return self.sum_total() / len(self._data_list)


class CSVReader:

    def __init__(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            lines = tuple(reader)
        if len(lines) < 3:
            raise ValueError("No data rows found in the CSV file.")
        self._lines = lines[1:]

    def parse_data(self) -> DataList:
        data_list = DataList()
        for i, row in enumerate(self._lines):
            row = [v.strip() for v in row]
            if not any(row):
                continue

            while len(row) < 3:
                row.append("")

            try:
                val_a = int(row[0]) if row[0] != "" else None
                val_b = int(row[1]) if row[1] != "" else None
                val_c = int(row[2]) if row[2] != "" else None
                data_list.append(Data(val_a, val_b, val_c))
            except ValueError:
                print(f"Row {i + 1} contains invalid data: {row!r}")
        return data_list


def main() -> None:
    data_file_path = r"C:\work\tmp_study\20250412_2133\data.csv"
    reader = CSVReader(data_file_path)
    data_list = reader.parse_data()

    print("Sum of totals:", data_list.sum_total())
    print("Average of totals:", data_list.avg_total())
    print("Data count:", len(data_list))


if __name__ == "__main__":
    main()
