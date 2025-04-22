import csv

# [課題]
# 以下は、あまり保守しやすくない例のレガシーコードです。グローバル変数の使用や、複数の責務が1つの関数にまとめられているなど、
# さまざまな問題があります。このコードを題材に、リファクタリングに取り組んでみてください。

# ■ リファクタリング時に着目したいポイント:
# グローバル変数の使用を減らす、もしくはやめる。
# I/O 処理と集計処理を分離し、関数を小さく保ち、責務を明確化する。
# エラー処理を整理し、不備のある行に対してどのように対応するか検討する。
# 再利用しやすいようにクラス化または関数分割を検討する。
# リファクタリングした結果、可読性と保守性が上がったかどうかを確認する。

# グローバル変数（好ましくない例）
data_file_path = "data.csv"
result_list = []

def process_data():
    global data_file_path
    global result_list

    # CSVを読み込んで、ある計算処理を行う
    with open(data_file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx == 0:
                # ヘッダーをスキップ
                continue
            elif len(row) < 3:
                # データ不備（エラー処理がない）
                print("Row has insufficient data:", row)
            else:
                # 適当に数値変換して詰め込む
                val_a = int(row[0])
                val_b = int(row[1])
                val_c = int(row[2])
                total = val_a + val_b + val_c
                result_list.append((val_a, val_b, val_c, total))

    # 計算結果を元に集計して出力（1つの関数で複数の責務）
    sum_total = 0
    for item in result_list:
        sum_total += item[3]

    avg_total = 0
    if len(result_list) != 0:
        avg_total = sum_total / len(result_list)

    print("Sum of totals:", sum_total)
    print("Average of totals:", avg_total)
    print("Data count:", len(result_list))

if __name__ == "__main__":
    process_data()
