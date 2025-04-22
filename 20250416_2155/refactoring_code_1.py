from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class City(Enum):
    Tokyo = "Tokyo"
    Osaka = "Osaka"


class Weather(Enum):
    Sunny = "Sunny"
    Cloudy = "Cloudy"
    Rainy = "Rainy"


@dataclass(frozen=True)
class Item:
    date: str
    city: City
    temperature: int
    humidity: int
    weather: Weather

    @staticmethod
    def from_raw_item(raw_item: dict[str, Any]) -> Item:
        return Item(
            date=raw_item["date"],
            city=City(raw_item["city"]),
            temperature=int(raw_item["temperature"]),
            humidity=int(raw_item["humidity"]),
            weather=Weather(raw_item["weather"]),
        )


class Data:

    def __init__(self, *, items: list[Item] | None = None) -> None:
        self._items = items or []

    def add(self, item: Item) -> Data:
        items = [*self._items, item]
        return Data(items=items)

    def get_item(self, condition: Callable[[list[Item]], Item]) -> Item:
        if not self._items:
            raise ValueError("No data available.")
        return condition(self._items)

    def extract(self, condition: Callable[[Item], bool]) -> Data:
        return Data(items=[item for item in self._items if condition(item)])

    def average_temperature(self) -> float:
        if not self._items:
            return 0.0
        return sum(item.temperature for item in self._items) / len(self._items)

    def average_temperature_on(self, city: City) -> float:
        data = self.extract(lambda item: item.city == city)
        return data.average_temperature()

    def average_humidity(self) -> float:
        if not self._items:
            return 0.0
        return sum(item.humidity for item in self._items) / len(self._items)

    def average_humidity_on(self, weather: Weather) -> float:
        data = self.extract(lambda item: item.weather == weather)
        return data.average_humidity()

    def get_item_on_max_temperature(self) -> Item:
        def condition(items: list[Item]) -> Item:
            return max(items, key=lambda item: item.temperature)

        return self.get_item(condition=condition)


def main() -> None:
    # 気象データ分析スクリプト
    raw_data = [
        {"date": "2023-01-01", "city": "Tokyo", "temperature": 5, "humidity": 45, "weather": "Sunny"},
        {"date": "2023-01-01", "city": "Osaka", "temperature": 8, "humidity": 50, "weather": "Cloudy"},
        {"date": "2023-01-02", "city": "Tokyo", "temperature": 6, "humidity": 48, "weather": "Rainy"},
        {"date": "2023-01-02", "city": "Osaka", "temperature": 9, "humidity": 55, "weather": "Rainy"},
        {"date": "2023-01-03", "city": "Tokyo", "temperature": 4, "humidity": 40, "weather": "Sunny"},
        {"date": "2023-01-03", "city": "Osaka", "temperature": 7, "humidity": 45, "weather": "Sunny"},
    ]

    items = [Item.from_raw_item(item) for item in raw_data]
    data = Data(items=items)

    # 東京の平均気温を計算
    tokyo_avg_temp = data.average_temperature_on(city=City.Tokyo)
    print(f"東京の平均気温: {tokyo_avg_temp}℃")

    # 大阪の平均気温を計算
    osaka_avg_temp = data.average_temperature_on(city=City.Osaka)
    print(f"大阪の平均気温: {osaka_avg_temp}℃")

    # 天気が「晴れ」の日の平均湿度を計算
    avg_sunny_humidity = data.average_humidity_on(weather=Weather.Sunny)
    print(f"晴れの日の平均湿度: {avg_sunny_humidity}%")

    # 最も暑かった日を見つける
    hottest_day = data.get_item_on_max_temperature()
    print(f"最も暑かった日: {hottest_day.date}、都市: {hottest_day.city}、気温: {hottest_day.temperature}℃")


if __name__ == "__main__":
    main()
