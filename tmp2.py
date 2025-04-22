import json
import os
import re
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Any, Optional, Set, ClassVar, Union, List, Type, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo


# 検証ロジックの抽象基底クラス
class Validator(ABC):
    @abstractmethod
    def validate(self, value: Any, field_name: str) -> bool:
        pass

    @abstractmethod
    def get_error_message(self, value: Any, field_name: str) -> str:
        pass


# ファイルパスの検証クラス
class FilePathValidator(Validator):
    def validate(self, value: Any, field_name: str) -> bool:
        if not isinstance(value, str):
            return False
        # 簡易的な検証（実際の存在チェックは必要に応じて）
        return Path(value).suffix != "" and not re.match(r'^https?://', value)

    def get_error_message(self, value: Any, field_name: str) -> str:
        return f"{field_name}は有効なファイルパスである必要があります: {value}"


# URLの検証クラス
class UrlValidator(Validator):
    def validate(self, value: Any, field_name: str) -> bool:
        if not isinstance(value, str):
            return False
        return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', value))

    def get_error_message(self, value: Any, field_name: str) -> str:
        return f"{field_name}はURLである必要があります: {value}"


# フィールドの型を表すEnum
class FieldType(Enum):
    FILE_PATH = auto()
    URL = auto()
    BOOLEAN = auto()
    ANY = auto()


# フィールド定義クラス
class FieldDefinition:
    def __init__(self, name: str, field_type: FieldType, required: bool = False):
        self.name = name
        self.field_type = field_type
        self.required = required

    def get_validator(self) -> Optional[Validator]:
        if self.field_type == FieldType.FILE_PATH:
            return FilePathValidator()
        elif self.field_type == FieldType.URL:
            return UrlValidator()
        return None


# 要件セットの基底クラス - パラメータや条件に基づいて必要なフィールドを定義
class RequirementSet(ABC):
    @abstractmethod
    def get_required_fields(self) -> List[FieldDefinition]:
        pass

    @abstractmethod
    def is_applicable(self, params: Dict[str, Any]) -> bool:
        pass


# パラメータ値に基づく要件セット
class ParamBasedRequirementSet(RequirementSet):
    def __init__(self, param_value: int, field_definitions: List[FieldDefinition]):
        self.param_value = param_value
        self.field_definitions = field_definitions

    def get_required_fields(self) -> List[FieldDefinition]:
        return self.field_definitions

    def is_applicable(self, params: Dict[str, Any]) -> bool:
        return params.get('param') == self.param_value


# key_a6の値に基づく要件セット
class KeyA6BasedRequirementSet(RequirementSet):
    def __init__(self, key_a6_value: bool, affected_fields: List[str]):
        self.key_a6_value = key_a6_value
        self.affected_fields = affected_fields

    def get_required_fields(self) -> List[FieldDefinition]:
        field_type = FieldType.URL if self.key_a6_value else FieldType.FILE_PATH
        return [FieldDefinition(name, field_type, False) for name in self.affected_fields]

    def is_applicable(self, params: Dict[str, Any]) -> bool:
        model_data = params.get('model_data', {})
        return model_data.get('key_a6') == self.key_a6_value


# 要件マネージャー - すべての要件セットを管理
class RequirementManager:
    def __init__(self):
        self.requirement_sets: List[RequirementSet] = []

    def add_requirement_set(self, requirement_set: RequirementSet) -> None:
        self.requirement_sets.append(requirement_set)

    def get_applicable_requirements(self, params: Dict[str, Any]) -> List[FieldDefinition]:
        requirements: List[FieldDefinition] = []
        for req_set in self.requirement_sets:
            if req_set.is_applicable(params):
                requirements.extend(req_set.get_required_fields())
        return requirements


# Pydanticモデルの基底クラス
class ValidatedModel(BaseModel):
    @classmethod
    def get_requirement_manager(cls) -> RequirementManager:
        if not hasattr(cls, '_requirement_manager'):
            cls._requirement_manager = RequirementManager()
            cls._initialize_requirements()
        return cls._requirement_manager

    @classmethod
    def _initialize_requirements(cls) -> None:
        """サブクラスで要件を初期化するためにオーバーライド"""
        pass

    def validate_fields(self, params: Dict[str, Any]) -> None:
        manager = self.__class__.get_requirement_manager()
        requirements = manager.get_applicable_requirements(params)

        # 必須フィールドの検証
        for req in requirements:
            if req.required and getattr(self, req.name, None) is None:
                raise ValueError(f"{req.name}は必須フィールドです")

            # 値の型検証
            value = getattr(self, req.name, None)
            if value is not None:
                validator = req.get_validator()
                if validator and not validator.validate(value, req.name):
                    raise ValueError(validator.get_error_message(value, req.name))


# JsonAModelの実装
class JsonAModel(ValidatedModel):
    key_a1: Optional[str] = None
    key_a2: Optional[str] = None
    key_a3: Optional[str] = None
    key_a4: Optional[str] = None
    key_a5: Optional[str] = None
    key_a6: Optional[bool] = None

    @classmethod
    def _initialize_requirements(cls) -> None:
        manager = cls.get_requirement_manager()

        # パラメータに基づく要件
        manager.add_requirement_set(ParamBasedRequirementSet(
            0, [FieldDefinition("key_a2", FieldType.FILE_PATH, True)]
        ))
        manager.add_requirement_set(ParamBasedRequirementSet(
            1, [FieldDefinition("key_a2", FieldType.FILE_PATH, True),
                FieldDefinition("key_a3", FieldType.FILE_PATH, True)]
        ))
        manager.add_requirement_set(ParamBasedRequirementSet(
            2, [FieldDefinition("key_a3", FieldType.FILE_PATH, True),
                FieldDefinition("key_a4", FieldType.FILE_PATH, True)]
        ))
        manager.add_requirement_set(ParamBasedRequirementSet(
            3, [FieldDefinition("key_a2", FieldType.FILE_PATH, True),
                FieldDefinition("key_a4", FieldType.FILE_PATH, True),
                FieldDefinition("key_a5", FieldType.FILE_PATH, True)]
        ))

        # key_a6に基づく要件
        manager.add_requirement_set(KeyA6BasedRequirementSet(
            True, ["key_a2", "key_a3"]
        ))
        manager.add_requirement_set(KeyA6BasedRequirementSet(
            False, ["key_a2", "key_a3"]
        ))

    @model_validator(mode='after')
    def validate_model(self) -> 'JsonAModel':
        self.validate_fields({
            'param': getattr(self.__class__, '_param', -1),
            'model_data': self.model_dump()
        })
        return self

    @classmethod
    def set_param(cls, param: int) -> None:
        cls._param = param


# JsonBModelの実装
class JsonBModel(ValidatedModel):
    key_b1: Optional[str] = None
    key_b2: Optional[str] = None

    @classmethod
    def _initialize_requirements(cls) -> None:
        manager = cls.get_requirement_manager()
        manager.add_requirement_set(ParamBasedRequirementSet(
            -1, [FieldDefinition("key_b1", FieldType.FILE_PATH, False),
                 FieldDefinition("key_b2", FieldType.FILE_PATH, False)]
        ))

    @model_validator(mode='after')
    def validate_model(self) -> 'JsonBModel':
        self.validate_fields({'param': -1, 'model_data': self.model_dump()})
        return self


# CombinedModelの実装
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


# ファクトリー関数 - JsonModelを生成
def create_json_a_model(data: Dict[str, Any], param: int) -> JsonAModel:
    JsonAModel.set_param(param)
    return JsonAModel(**data)


def parse_json_files(json_a_path: str, json_b_path: str, param: int) -> CombinedModel:
    # JSONファイルの読み込み
    with open(json_a_path, 'r') as f:
        json_a_data = json.load(f)

    with open(json_b_path, 'r') as f:
        json_b_data = json.load(f)

    # 検証を実行
    combined_model = CombinedModel(
        json_a=create_json_a_model(json_a_data, param),
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

# 新しいモデルやルールを追加する場合の手順は簡単です：
#
# 必要に応じて新しいValidatorクラスを作成
# 新しいRequirementSetを作成して条件を定義
# ValidatedModelを継承した新しいモデルクラスを作成
# _initialize_requirementsメソッドをオーバーライドして要件を定義
"""
# 新しいバリデータの追加
class DateFormatValidator(Validator):
    def validate(self, value: Any, field_name: str) -> bool:
        if not isinstance(value, str):
            return False
        try:
            # YYYY-MM-DD形式かチェック
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def get_error_message(self, value: Any, field_name: str) -> str:
        return f"{field_name}はYYYY-MM-DD形式の日付である必要があります: {value}"

# FieldTypeに新しい型を追加
class FieldType(Enum):
    FILE_PATH = auto()
    URL = auto()
    BOOLEAN = auto()
    DATE = auto()  # 追加
    ANY = auto()

# FieldDefinitionクラスのget_validatorメソッドを更新
def get_validator(self) -> Optional[Validator]:
    if self.field_type == FieldType.FILE_PATH:
        return FilePathValidator()
    elif self.field_type == FieldType.URL:
        return UrlValidator()
    elif self.field_type == FieldType.DATE:  # 追加
        return DateFormatValidator()
    return None

# 新しい要件セットの定義
class DateBasedRequirementSet(RequirementSet):
    def __init__(self, date_field: str, dependent_fields: List[str]):
        self.date_field = date_field
        self.dependent_fields = dependent_fields
    
    def get_required_fields(self) -> List[FieldDefinition]:
        return [FieldDefinition(name, FieldType.FILE_PATH, True) for name in self.dependent_fields]
    
    def is_applicable(self, params: Dict[str, Any]) -> bool:
        model_data = params.get('model_data', {})
        # 日付フィールドが存在する場合に適用
        return self.date_field in model_data and model_data[self.date_field] is not None

# 新しいモデルの定義
class JsonCModel(ValidatedModel):
    key_c1: Optional[str] = None
    key_c2: Optional[str] = None
    date_field: Optional[str] = None
    
    @classmethod
    def _initialize_requirements(cls) -> None:
        manager = cls.get_requirement_manager()
        
        # 基本的な要件
        manager.add_requirement_set(ParamBasedRequirementSet(
            -1, [FieldDefinition("key_c1", FieldType.FILE_PATH, True)]
        ))
        
        # 日付フィールドが存在する場合の要件
        manager.add_requirement_set(DateBasedRequirementSet(
            "date_field", ["key_c2"]
        ))
    
    @model_validator(mode='after')
    def validate_model(self) -> 'JsonCModel':
        self.validate_fields({
            'param': -1,
            'model_data': self.model_dump()
        })
        return self

"""

# 既存のモデルに新しい要件を追加する場合も簡単です：
"""
# JsonAModelに新しい要件を追加
@classmethod
def _initialize_requirements(cls) -> None:
    manager = cls.get_requirement_manager()
    
    # 既存の要件（前述のコードと同じ）
    # ...
    
    # 新しい要件を追加
    manager.add_requirement_set(ParamBasedRequirementSet(
        4, [FieldDefinition("key_a3", FieldType.URL, True),
            FieldDefinition("key_a5", FieldType.URL, True)]
    ))
"""

# さらに複雑なケースでは、Pydantic v2の「ディスクリミネーテッドユニオン」機能を活用できます：
"""
from typing import Union, Literal
from pydantic import Field, discriminated_union_tag

class BaseJsonModel(ValidatedModel):
    model_type: str  # ディスクリミネータフィールド

class TypeAModel(BaseJsonModel):
    model_type: Literal["type_a"] = "type_a"
    key_a1: str
    key_a2: Optional[str] = None

class TypeBModel(BaseJsonModel):
    model_type: Literal["type_b"] = "type_b"
    key_b1: str
    key_b2: Optional[str] = None

# ディスクリミネーテッドユニオンの定義
JsonModelUnion = Union[TypeAModel, TypeBModel]

# 使用例
def process_json_model(model_data: Dict[str, Any]) -> BaseJsonModel:
    # model_typeフィールドに基づいて適切なモデルを自動選択
    model_type = model_data.get("model_type")
    if model_type == "type_a":
        return TypeAModel(**model_data)
    elif model_type == "type_b":
        return TypeBModel(**model_data)
    else:
        raise ValueError(f"不明なモデルタイプ: {model_type}")
"""

# Pydantic v2では、ディスクリミネーテッドユニオンの扱いが改善され、
# discriminatorパラメータを使って明示的に判別フィールドを指定できます：
"""
from typing import Annotated, Union
from pydantic import BaseModel, Field, Discriminator

class Animal(BaseModel):
    type: str

class Dog(Animal):
    type: Literal["dog"] = "dog"
    bark_sound: str

class Cat(Animal):
    type: Literal["cat"] = "cat"
    meow_sound: str

# discriminatorを使った定義
AnimalUnion = Annotated[Union[Dog, Cat], Discriminator("type")]

# JSONからの解析
def parse_animal(data: dict) -> AnimalUnion:
    # typeフィールドを見て、自動的に適切なクラスを選択
    return AnimalUnion.model_validate(data)

# 使用例
animal_data = {"type": "dog", "bark_sound": "Woof!"}
animal = parse_animal(animal_data)  # 自動的にDog型として解析される
"""