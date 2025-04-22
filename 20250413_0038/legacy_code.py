import time

import requests

# 次の課題として、以下に示すレガシーコードをリファクタリングしましょう。
# 今回のコードは、API からユーザー情報を取得しようとする簡単な処理を行っていますが、以下のような問題点を含んでいます。
#
# • グローバル変数(API_KEY)を直接参照しており、切り替えやテストがしづらい。
# • API 失敗時のリトライ処理が再帰呼び出しになっており、仕組みがわかりにくい。
# • リクエスト時に固定の待ち時間(wait_time)が指定されており、効率が悪い可能性がある。
# • 1件ずつ同期呼び出しをしているため、ユーザー数が多いときに時間がかかる可能性がある。
# • 特に複数のユーザーを並列で処理したい場合、スレッドや非同期 I/O などを検討してもよい。
# • エラー処理やログ出力は標準出力への print() のみで簡易的。状況に応じて拡張したい。
#
# 課題:
# グローバル定数 API_KEY の扱いを工夫する(クラスや設定ファイル、環境変数などで柔軟に保持できるように)。
# 再帰呼び出しによるリトライではなく、ループやセパレートされたリトライ用の仕組みで実装する。
# (任意) スレッドや非同期 I/O (asyncio) などを使い、複数ユーザーを同時に API に問い合わせられるよう検討する。
# 適切なエラー処理(例外を使う、ログを出力する、リトライ可能上限を設けるなど)。
# 型ヒント、docstring、リファクタリング手法(関数分割やクラス化など)で可読性と保守性を向上させる。

API_KEY = "SAMPLE_KEY"


def fetch_data(user_id, wait_time):
    url = "https://example.com/api/get_user_info"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"user_id": user_id},
    )
    if response.status_code == 429:
        print("Hit rate limit. Waiting...")
        time.sleep(wait_time)
        return fetch_data(user_id, wait_time * 2)  # 再帰呼び出し
    elif response.status_code == 200:
        data = response.json()
        return data
    else:
        print("Error fetching data:", response.status_code)
        return None


def main():
    for uid in range(1, 11):
        user_data = fetch_data(uid, 1)
        if user_data is not None:
            # 仮の処理 (本来はパースや保存など)
            print(f"User {uid} data: {user_data}")
        else:
            print(f"Skipping user {uid}")


if __name__ == "__main__":
    main()
