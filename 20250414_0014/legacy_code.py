import csv
import datetime

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


# グローバル変数: 設定・データファイルのパス、レポートの出力先などが直書きされている
STOCK_DATA_PATH = "stock_data.csv"
REPORT_OUTPUT_PATH = "report.txt"
GENERATE_TIMESTAMP = True


def generate_report() -> None:
    """
    在庫データを CSV ファイル(stock_data.csv)から読み込み、
    在庫数・仕入れ金額・出荷数などをまとめた簡単なレポートを
    report.txtとして出力する。
    """
    # 変数の初期化 (本来は構造化して保持したいデータ)
    total_item_count = 0
    total_cost = 0
    total_sold = 0

    # CSVファイルを読み込みながら在庫データを集計
    with open(STOCK_DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 不正データはスキップ - ログ出力もない
            if "item_count" not in row or "cost_each" not in row or "sold" not in row:
                continue
            try:
                item_count = int(row["item_count"])
                cost_each = int(row["cost_each"])
                sold = int(row["sold"])
            except ValueError:
                # 数値変換に失敗した場合スキップ
                continue

            total_item_count += item_count
            total_cost += cost_each * item_count
            total_sold += sold

    # レポートを出力する
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as out:
        out.write("===== Inventory Report =====\n")
        out.write(f"Total items in stock: {total_item_count}\n")
        out.write(f"Total cost of stock: {total_cost}\n")
        out.write(f"Total sold: {total_sold}\n")

        # 実行時のタイムスタンプ付加（今回は単純なフラグで制御）
        if GENERATE_TIMESTAMP:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            out.write(f"Report generated at: {now_str}\n")


def main() -> None:
    generate_report()
    print("Report generation completed.")


if __name__ == "__main__":
    main()
