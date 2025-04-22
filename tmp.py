import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Set, ClassVar, Union, Annotated
from pydantic import BaseModel, field_validator, model_validator, Field, ValidationInfo


# ファイルパスとURLを検証する関数
def is_valid_file_path(path: str) -> bool:
    # 実際のファイルの存在チェックが必要な場合はコメントを外してください
    # return os.path.isfile(path)
    # 簡易的な検証（拡張子があるかなど）
    return Path(path).suffix != "" and not re.match(r'^https?://', path)


def is_valid_url(url: str) -> bool:
    # 簡易的なURL検証
    return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', url))


class JsonAModel(BaseModel):
    # オプショナルとして定義
    key_a1: Optional[str] = None
    key_a2: Optional[str] = None
    key_a3: Optional[str] = None
    key_a4: Optional[str] = None
    key_a5: Optional[str] = None
    key_a6: Optional[bool] = None  # 追加: URLかファイルパスかを決めるフラグ

    # クラス変数としてparamを定義
    _param: ClassVar[int] = -1

    @classmethod
    def set_param(cls, param: int) -> None:
        cls._param = param

    @field_validator('key_a2', 'key_a3', mode='after')
    def validate_path_or_url(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if v is None:
            return v

        # 現在のモデルのインスタンスから key_a6 の値を取得
        model_data = info.data
        is_url = model_data.get('key_a6', False)

        if is_url:
            # URLの検証
            if not is_valid_url(v):
                raise ValueError(f"{info.field_name}はURLである必要があります: {v}")
        else:
            # ファイルパスの検証
            if not is_valid_file_path(v):
                raise ValueError(f"{info.field_name}は有効なファイルパスである必要があります: {v}")

        return v

    @field_validator('key_a1', 'key_a4', 'key_a5', mode='after')
    def validate_file_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_valid_file_path(v):
            raise ValueError(f"値は有効なファイルパスである必要があります: {v}")
        return v

    @model_validator(mode='after')
    def validate_keys_based_on_param(self) -> 'JsonAModel':
        # param値に基づいて必須キーを設定
        required_keys: Set[str] = set()
        param = self.__class__._param

        if param == 0:
            required_keys = {"key_a2"}
        elif param == 1:
            required_keys = {"key_a2", "key_a3"}
        elif param == 2:
            required_keys = {"key_a3", "key_a4"}
        elif param == 3:
            required_keys = {"key_a2", "key_a4", "key_a5"}

        # 必須キーのチェック
        for key in required_keys:
            if getattr(self, key) is None:
                raise ValueError(f"param={param}の場合、{key}は必須です")

        # 不要なキーを削除する代わりに警告を出す（オプション）
        all_possible_keys = {"key_a2", "key_a3", "key_a4", "key_a5"}
        keys_to_ignore = all_possible_keys - required_keys
        for key in keys_to_ignore:
            if getattr(self, key) is not None:
                print(f"警告: param={param}の場合、{key}は無視されます")

        return self


class JsonBModel(BaseModel):
    # オプショナルとして定義
    key_b1: Optional[str] = None
    key_b2: Optional[str] = None

    @field_validator('key_b1', 'key_b2', mode='after')
    def validate_file_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_valid_file_path(v):
            raise ValueError(f"値は有効なファイルパスである必要があります: {v}")
        return v


class CombinedModel(BaseModel):
    json_a: JsonAModel
    json_b: JsonBModel

    @model_validator(mode='after')
    def validate_dependencies(self) -> 'CombinedModel':
        # key_a1が存在する場合、key_b1とkey_b2も必要
        if self.json_a.key_a1 is not None:
            if self.json_b.key_b1 is None:
                raise ValueError("json_a.key_a1が定義されている場合、json_b.key_b1は必須です")
            if self.json_b.key_b2 is None:
                raise ValueError("json_a.key_a1が定義されている場合、json_b.key_b2は必須です")

        return self


def parse_json_files(json_a_path: str, json_b_path: str, param: int) -> CombinedModel:
    # JSONファイルの読み込み
    with open(json_a_path, 'r') as f:
        json_a_data = json.load(f)

    with open(json_b_path, 'r') as f:
        json_b_data = json.load(f)

    # パラメータをモデルに設定
    JsonAModel.set_param(param)

    # 検証を実行
    combined_model = CombinedModel(
        json_a=JsonAModel(**json_a_data),
        json_b=JsonBModel(**json_b_data)
    )

    return combined_model


# 使用例
def main():
    try:
        result = parse_json_files('json_a.json', 'json_b.json', param=2)
        print("バリデーション成功:", result.model_dump())
    except ValueError as e:
        print("バリデーションエラー:", e)


if __name__ == "__main__":
    main()
