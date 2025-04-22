from __future__ import annotations

import csv
import datetime
from dataclasses import dataclass


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


class StockDataReader:

    def __init__(self, data_path: str) -> None:
        # CSVファイルを読み込みながら在庫データを集計
        with open(data_path, "r", encoding="utf-8") as f:
            self._reader = csv.DictReader(f)

    def parse_data(self) -> StockDataList:
        stock_data_list = StockDataList()
        for row in self._reader:
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


class Report:

    def __init__(self) -> None:
        self._total_item_count = None
        self._total_cost = None
        self._total_sold = None
        self._timestamp = False

    def add_total_item_count(self, total_item_count: int) -> None:
        self._total_item_count = total_item_count

    def add_total_cost(self, total_cost: int) -> None:
        self._total_cost = total_cost

    def add_total_sold(self, total_sold: int) -> None:
        self._total_sold = total_sold

    def add_timestamp(self) -> None:
        self._timestamp = True

    def generate(self, output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write("===== Inventory Report =====\n")
            if self._total_item_count is not None:
                out.write(f"Total items in stock: {self._total_item_count}\n")
            if self._total_cost is not None:
                out.write(f"Total cost of stock: {self._total_cost}\n")
            if self._total_sold is not None:
                out.write(f"Total sold: {self._total_sold}\n")
            if self._timestamp:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                out.write(f"Report generated at: {now_str}\n")


def main() -> None:
    stock_data_path = "stock_data.csv"
    report_output_path = "report.txt"

    reader = StockDataReader(stock_data_path)
    data_list = reader.parse_data()

    report = Report()
    report.add_total_item_count(data_list.total_item_count)
    report.add_total_cost(data_list.total_cost)
    report.add_total_sold(data_list.total_sold)
    report.add_timestamp()
    report.generate(report_output_path)
    print("Report generation completed.")


if __name__ == "__main__":
    main()
