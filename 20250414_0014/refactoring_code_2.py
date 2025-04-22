from __future__ import annotations

import csv
import datetime
import json
from dataclasses import dataclass
from io import StringIO
from typing import Protocol, IO


# ────────────────────────────────────────────────────────
# ▼ 構造上の問題点・リファクタリングのヒント
# ────────────────────────────────────────────────────────
#
# グローバル変数が複数存在 (STOCK_DATA_PATH、REPORT_OUTPUT_PATH、GENERATE_TIMESTAMP)。
# → クラスや設定ファイル、環境変数等で管理するなど、使う場所を制限し、引数として受け取れるようにすると保守性が上がります。
#
# 1つの関数 generate_report が「データの読み込み・集計」「データの検証（バリデーション）」「レポート作成・出力」の複数の責務を持っている。
# → 関数を適切に分割する、もしくはクラスに責務を分けて持たせるなど構成を見直すと良いでしょう。
#
# 異常値やログ出力について、単にスキップしているだけで詳細なエラー処理や再試行、警告をログに出す仕組みがない。
# → 例外の取り扱い・ログの出力など、構造面で拡張しやすいように設計するとよいです。
#
# 将来、複数のレポート形式（JSON や PDF など）を追加する可能性がある場合、ファイル出力部分を一箇所にまとめておくと変更が容易になり、依存を分離できます。
#
# パスやフラグの扱い
# → コマンドライン引数や環境変数などで外部から受け取りたい場合、引数を関数に渡せるようにするとテストしやすくなります。
#
# ────────────────────────────────────────────────────────
# ▼ 課題
# ────────────────────────────────────────────────────────
#
# 今回のスクリプトは「在庫データをまとめたレポートを作成する」目的自体はそのままに、構造(設計)を改善してください。
# コードを実行したときの最終的な結果（report.txtの内容や標準出力メッセージ）は同じでも、
# クラス化・関数分割・設定管理のしやすさなどを念頭に、保守しやすい形を目指してみましょう。
# 具体的には以下を検討してください:
# • グローバル変数を使用せず、適切に依存関係を注入する。
# • 読み込み部分、集計部分、レポート出力部分を分離し、関数/クラスを適切に切り出す。
# • バリデーションやエラー処理（不正行・数値変換の失敗時のログなど）をどのように拡張しやすい設計にするか考える。
# • 今後、レポートの出力先が増えることを想定し、出力方式を抽象化するなども検討する。

# [添削]
# 以下の点で、コードが以前のレガシーコードに比べて大きく改善されており、とても良いリファクタリングになっています。
#
# グローバル変数を撤廃し、クラスや引数等を通じて依存関係を管理している。
# データ構造 (StockData, StockDataList)・読み込み担当 (StockDataReader)・レポート生成担当 (Report) といった役割分担が明確化されている。
# レポート出力処理がひとつのメソッド (Report.generate) に集約されていて、将来 JSON や PDF 出力に切り替えたいときの拡張がしやすい。
# 特に「構造の変更が主目的」という狙いに沿って、責務が分離され可読性・保守性が向上しているのは高く評価できます。
# 以下、さらなる改善や拡張検討の例をいくつか挙げますので、ご参考にしてください。
#
# ────────────────────────────────────────────────────────
# 1) メンバー変数の追加/編集まわり
# ────────────────────────────────────────────────────────
# • Report クラスの add_total_cost() の呼び出しが 2 回連続 (report.add_total_cost(data_list.total_item_count)、
# 　report.add_total_cost(data_list.total_cost)) となっています。おそらくタスクが
#   「item_count の合計」「単価合計」をまとめる意図だったのが、メソッド名を間違って呼んでいると思われます。
#   本来は「add_total_item_count(data_list.total_item_count)」と「add_total_cost(data_list.total_cost)」と
# 　呼ぶのではないでしょうか。
# 　こうしたバグが埋もれないようにするには、テストの導入や命名ルールの厳格化などを加味すると、より堅牢になります。
# • Report クラスに各種 add_XXX() メソッドが用意されていますが、もしレポート内容が増えてきた場合は、
# 　単に値を代入するメソッドが増え過ぎる可能性があります。
# 　たとえば 「レポートに書きたい情報をまとめた DTO (Data Transfer Object)」や辞書を引数に受け取り、
# 　一度にまとめて設定するような仕掛けを設けるのも手です。
#
# ────────────────────────────────────────────────────────
# 2) バリデーションやエラーハンドリング
# ────────────────────────────────────────────────────────
# • 不正行をスキップするだけでなく、将来的にログ出力を行ったり、例外にして呼び出し元に通知するなど拡張反映する際、
# 　現状のような構造になっていると取り組みやすいです。
#
# 例: 「どの行でエラーが起こったか」を記録して後からまとめて確認できる仕組み
# 例: パースできない行を別のファイルに書き出し、保留扱いにする仕組み
#
# ────────────────────────────────────────────────────────
# 3) 出力先の柔軟化
# ────────────────────────────────────────────────────────
# • Report クラスの generate メソッドが現状はテキストファイル出力に限定されています。
#
# 将来、レポートを JSON や Excel (XLSX) などで出力したい場合、出力手段を抽象化するインターフェース
# (例: ReportWriter という抽象クラスや Protocol を用意) があれば、Report クラスはそのインターフェースに依存し、
# 実際のファイル出力やコンソール出力は別の実装クラスに任せる設計にできます。
# 本格的に拡張したい場合は、「レポート内容」のオブジェクトと「出力方法」を分離し、
# IoC (Inversion of Control) 的に実装するパターンも考えられます。
#
# ────────────────────────────────────────────────────────
# 4) テストのしやすさ
# ────────────────────────────────────────────────────────
# • 現状の実装はまだ一連の処理(main関数)とファイル I/O が密結合しています。
# 　将来、ユニットテストを組もうとすると、実ファイル(stock_data.csv や report.txt)を生成してしまうことになるかもしれません。
#
# もしテスト分離のニーズがある場合、Reader や Reporter にストリームやファイルパスではなく
# 抽象的なインターフェース (StringIO のような仮想ストリーム) を受け取れるようにしておくと、
# ファイルへの依存を切り離してテストできるようになります。
# StockDataReader.init で「open するファイルを指定している部分」をもう一段ラップして、
# 呼び出し側で「ファイルパスを渡すか、あるいはStringIOを渡すか」などをコントロールする方法が一例です。

# [質問①]
# 「1) メンバー変数の追加/編集まわり」のの「「レポートに書きたい情報をまとめた DTO (Data Transfer Object)」や辞書を引数に受け取り、
# 一度にまとめて設定するような仕掛けを設けるのも手です。」の部分について、StockDataListをDTOとして使用してもいでしょうか?
# それとも別途クラスを用意した方が良いでしょうか?
#
# [回答①]
# StockDataList をそのままレポート用の DTO として使うアプローチも可能ですが、
# 個人的には「別途クラスやデータ構造(あるいは単純な dict など)を用意する」ほうが、
# 責務の分離という観点でより柔軟になるケースが多いです。以下でメリット・デメリットを比較してみます。
#
# ────────────────────────────────────────────────────────
# 1) StockDataList をそのまま DTO として利用する場合
# ────────────────────────────────────────────────────────
# ■ メリット
# • 新たにクラスや構造を作るコストがかからない。
# • すでに total_item_count / total_cost / total_sold などのプロパティが定義されているので、そのまま値が取り出せる。
# ■ デメリット
# • レポートで必要な項目と、StockDataList が持つプロパティ(またはメソッド)が常に一致するとは限らない。
# 　将来レポート項目の追加や変更があったとき、「在庫管理上は不要だがレポート上は必要な値」が発生するかもしれない。
# • StockDataList は「在庫情報をまとめて保持し、集計するためのクラス」という役割を担っている。
# 一方、DTO (Data Transfer Object) は主に「別のレイヤーにデータを渡すためのシンプルなコンテナ」として期待されることが多い。
# たとえば「集計のためのロジック」まで含むクラスを「レポートのための転送用」に使うと、テスト・責務がやや混在しがちになる。
#
# ────────────────────────────────────────────────────────
# 2) 別途 DTO クラス（もしくは単純な dict）を用意する場合
# ────────────────────────────────────────────────────────
# ■ メリット
# • レポートに必要な情報を「レポート用 DTO」として一括管理できる。たとえば下記のようにする案:
#
# @dataclass
# class ReportData:
#   total_item_count: int
#   total_cost: int total_sold: int
#   # 他にレポート固有の項目が増えるならここに追加
#
# そしてメソッドなどは持たせず、あくまで転送専用の最小限のデータ構造として扱う。
# • レポートに必要な数字をまとめて set する、もしくはコンストラクタで渡すなど、一度に並べて設定できる。
# • レポート内容が増減してもそれに対応したプロパティ/フィールドをこの DTO に集約しておけば、
#  StockDataList 側の仕様変更を最小限に抑えられる(=変更の影響範囲が小さくなる)。
#
# ■ デメリット
# • 新たなクラスを定義・管理するコストがかかる。
# • ほとんど StockDataList の集計値を移し替えるだけの場合、コード量がやや増える。
#
# ────────────────────────────────────────────────────────
# 3) 使い分けの考え方
# ────────────────────────────────────────────────────────
# • スモールスタートで、レポート対象が StockDataList の集計済み値程度に収まるなら、
# 　当面は StockDataList のプロパティを直接呼び出しても大きな問題にはならないでしょう。
# • しかし、レポートに固有の情報(たとえば特定のフォーマットで日付を表示するとか、ユーザー向けに加工した文字列を追加するとか)が増えてくると、
# 　「在庫管理(=StockDataList)の責務」と「レポートの責務」が段々と混ざってきてしまいます。
# • 将来的にレポートの拡張が見込まれる(たとえば複数形式のレポートを生成する、在庫管理とは関係のない指標も出す…など)、
# 　あるいは保守チームが分かれているような場合は、早い段階で ReportData のような「レポートに必要な項目をまとめた軽量オブジェクト」を
# 　用意したほうが見通しが良くなります。
#
# ────────────────────────────────────────────────────────
# まとめ
# ────────────────────────────────────────────────────────
# • 小規模・限定的な用途なら、StockDataList を使っても問題ありません。
# • 将来的な拡張や責務の明確化を考えるなら、別途 DTO (データ保存専用クラスや dict) を用意するほうが望ましいケースが多いです。
# • 責務をしっかり分けたいのであれば、StockDataList は在庫集計用 (ドメインロジック)、
# 　ReportData はレポート用データ転送 (DTO)、Report クラスは出力専用ロジック、といった設計にすると保守性が上がるでしょう。

@dataclass(frozen=True)
class StockData:
    item_count: int
    cost_each: int
    sold: int

    @property
    def cost(self) -> int:
        return self.item_count * self.cost_each

    @staticmethod
    def is_valid_row(row: dict[str, str]) -> bool:
        return all(
            key in row
            for key in ("item_count", "cost_each", "sold")
        )

    @staticmethod
    def make_from_row(row: dict[str, str]) -> StockData:
        return StockData(
            item_count=int(row["item_count"]),
            cost_each=int(row["cost_each"]),
            sold=int(row["sold"]),
        )


class StockDataList:

    def __init__(self) -> None:
        self._data_list: list[StockData] = []

    @property
    def total_item_count(self) -> int:
        return sum(data.item_count for data in self._data_list)

    @property
    def total_cost(self) -> int:
        return sum(data.cost for data in self._data_list)

    @property
    def total_sold(self) -> int:
        return sum(data.sold for data in self._data_list)

    def append(self, data: StockData) -> None:
        self._data_list.append(data)


class StockDataSource(Protocol):
    def open_stream(self) -> IO[str]: ...


class FileDataSource:

    def __init__(self, path: str):
        self._path = path

    def open_stream(self) -> IO[str]:
        # ファイルを開いてテキストIOを返す
        return open(self._path, "r", encoding="utf-8")


class InMemoryDataSource:

    def __init__(self, csv_content: str):
        self._csv_content = csv_content

    def open_stream(self) -> IO[str]:
        # StringIO を返す
        return StringIO(self._csv_content)


class StockDataReader:

    def __init__(self, data_source: StockDataSource) -> None:
        self._data_source = data_source

    def parse_data(self) -> StockDataList:
        stock_data_list = StockDataList()

        with self._data_source.open_stream() as stream:
            reader = csv.DictReader(stream)
            for row in reader:
                # 不正データはスキップ - ログ出力もない
                if not StockData.is_valid_row(row):
                    continue
                try:
                    stock_data = StockData.make_from_row(row)
                    stock_data_list.append(stock_data)
                except ValueError:
                    # 数値変換に失敗した場合スキップ
                    continue
        return stock_data_list


@dataclass(frozen=True)
class ReportData:
    total_item_count: int
    total_cost: int
    total_sold: int
    need_timestamp: bool


class ReportWriter(Protocol):
    def write_report(self, data: ReportData) -> None: ...


class TextReportWriter:
    def __init__(self, output_path: str) -> None:
        self._output_path = output_path

    def write_report(self, data: ReportData) -> None:
        with open(self._output_path, "w", encoding="utf-8") as f:
            f.write("===== Inventory Report =====\n")
            f.write(f"Total items in stock: {data.total_item_count}\n")
            f.write(f"Total cost of stock: {data.total_cost}\n")
            f.write(f"Total sold: {data.total_sold}\n")
            if data.need_timestamp:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"Report generated at: {now_str}\n")


class JsonReportWriter:
    def __init__(self, output_path: str) -> None:
        self._output_path = output_path

    def write_report(self, data: ReportData) -> None:
        # 辞書に変換して JSON dump
        report_dict = {
            "total_item_count": data.total_item_count,
            "total_cost": data.total_cost,
            "total_sold": data.total_sold,
        }
        if data.need_timestamp:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_dict["generated_at"] = now_str
        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)


class Report:

    def __init__(self, writer: ReportWriter) -> None:
        self._writer = writer

    def generate(self, data: ReportData) -> None:
        self._writer.write_report(data)


def main() -> None:
    stock_data_path = "stock_data.csv"
    report_output_path = "report.txt"

    file_source = FileDataSource(stock_data_path)
    reader = StockDataReader(file_source)
    data_list = reader.parse_data()

    report_data = ReportData(
        total_item_count=data_list.total_item_count,
        total_cost=data_list.total_cost,
        total_sold=data_list.total_sold,
        need_timestamp=True,
    )
    writer = TextReportWriter(report_output_path)
    report = Report(writer)
    report.generate(report_data)
    print("Report generation completed.")


if __name__ == "__main__":
    main()
