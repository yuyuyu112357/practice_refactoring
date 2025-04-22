import asyncio
import os

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
# [課題]
# グローバル定数 API_KEY の扱いを工夫する(クラスや設定ファイル、環境変数などで柔軟に保持できるように)。
# 再帰呼び出しによるリトライではなく、ループやセパレートされたリトライ用の仕組みで実装する。
# (任意) スレッドや非同期 I/O (asyncio) などを使い、複数ユーザーを同時に API に問い合わせられるよう検討する。
# 適切なエラー処理(例外を使う、ログを出力する、リトライ可能上限を設けるなど)。
# 型ヒント、docstring、リファクタリング手法(関数分割やクラス化など)で可読性と保守性を向上させる。

# [添削]
# 以下に、リファクタリング後のコードに対するレビューと、さらなる改善点をまとめます。
# 全体として、グローバル変数ではなく環境変数を使う点や、再帰ではなくループによるリトライ処理に変更している点、
# asyncio を使った非同期処理を導入している点など、大きく改善されておりとても良い実装です。
#
# ────────────────────────────────────────────────────────
# 1) 非同期 I/O ライブラリの利用
# ────────────────────────────────────────────────────────
# • せっかく asyncio を使っているので、HTTP クライアントも非同期対応のもの (aiohttp 等) を使うと、
# 　リクエスト待機時間をブロックせずに並行処理が可能になります。現在の実装だと、
# 　requests が同期 I/O なのでメインスレッドをブロックしてしまい、真の並列化ができません。
# • 同期 I/O で問題がない場合はそのままでもかまいませんが、大幅なパフォーマンス向上が得られる可能性があるため、
# 　将来的な拡張を考えるなら検討するとよいでしょう。
#
# ────────────────────────────────────────────────────────
# 2) ロギングと例外処理
# ────────────────────────────────────────────────────────
# • 現在は print によるログ出力のみなので、将来的にファイル出力やログレベルの管理 (INFO/WARN/ERROR など) が
# 　必要になる場面があるかもしれません。標準ライブラリの logging モジュールを使い、メッセージ内容・レベル・出力先などを
# 　柔軟に調整できる仕組みにしておくと保守性が上がります。
# • 429 以外のステータスコード 4XX や 5XX に対しても、必要に応じてエラーとみなしてリトライ対象に含めるかどうかを検討し、
# 　処理方針を決めておくと良いでしょう。
#
# ────────────────────────────────────────────────────────
# 3) リトライ回数と上限
# ────────────────────────────────────────────────────────
# • リトライを 10 回試みたのち、すべて失敗したら終了するロジックを実装していますが、ビジネスロジックによっては wait_time の増え方や、
# 　リトライ回数を再度設定ファイルや環境変数などで外部から注入することを検討してもよいでしょう。
# 　リトライまわりの設定をユーザー(運用担当者)が調整できるようにしておくと、さらに運用しやすくなります。
#
# ────────────────────────────────────────────────────────
# 4) 並行処理の最適化
# ────────────────────────────────────────────────────────
# • 複数のユーザーを問い合わせる箇所 (range(1, 11) 部分) を asyncio.gather(...) などで並列処理すると、
# 　ユーザー毎の処理を同時に投げられて効率的です。
# • 同時リクエスト数に制限がある場合は、asyncio.Semaphore などを組み合わせてリクエスト数を制限しながら並列化を行うと、
# 　API が混乱せず、しかも多数のユーザーを高速に処理できるようになります。


class DataFetcher:

    def __init__(self, url: str, api_key: str, user_id: str) -> None:
        self._url = url
        self._api_key = api_key
        self._user_id = user_id
        self._response = self._get(self._url, self._api_key, self._user_id)

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def data(self) -> dict:
        return self._response.json()

    def retry(self) -> None:
        self._response = self._get(self._url, self._api_key, self._user_id)

    @staticmethod
    def _get(url: str, api_key: str, user_id: str) -> requests.Response:
        return requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"user_id": user_id},
        )


class RetryDataFetcher:

    def __init__(self, fetcher: DataFetcher, total: int, wait_time: int, retry_status: list[int]) -> None:
        self._fetcher = fetcher
        self._total = total
        self._wait_time = wait_time
        self._retry_status = retry_status

    async def start(self) -> None:
        for _ in range(self._total):
            if self._fetcher.status_code not in self._retry_status:
                break
            print("Hit rate limit. Waiting...")
            await asyncio.sleep(self._wait_time)
            self._wait_time *= 2
            self._fetcher.retry()
        else:
            print("Failed to fetch data")


async def fetch_data(url: str, api_key: str, user_id: str) -> None:
    data_fetcher = DataFetcher(
        url=url,
        api_key=api_key,
        user_id=str(user_id),
    )

    # リトライ処理を追加
    if data_fetcher.status_code == 429:
        retry_data_fetcher = RetryDataFetcher(
            fetcher=data_fetcher,
            total=10,
            wait_time=1,
            retry_status=[429],
        )
        await retry_data_fetcher.start()

    # データ取得
    if data_fetcher.status_code == 200:
        print(f"User {user_id} data: {data_fetcher.data}")
    else:
        print("Error fetching data:", data_fetcher.status_code)
        print(f"Skipping user {user_id}")


async def main() -> None:
    # .env ファイルから API_KEY を取得する
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY is not set")

    user_ids = range(1, 11)
    tasks = [
        fetch_data(
            url="https://example.com/api/get_user_info",
            api_key=api_key,
            user_id=str(uid),
        )
        for uid in user_ids
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
