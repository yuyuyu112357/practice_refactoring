# 気象データ分析スクリプト
data = [
    {"date": "2023-01-01", "city": "Tokyo", "temperature": 5, "humidity": 45, "weather": "Sunny"},
    {"date": "2023-01-01", "city": "Osaka", "temperature": 8, "humidity": 50, "weather": "Cloudy"},
    {"date": "2023-01-02", "city": "Tokyo", "temperature": 6, "humidity": 48, "weather": "Rainy"},
    {"date": "2023-01-02", "city": "Osaka", "temperature": 9, "humidity": 55, "weather": "Rainy"},
    {"date": "2023-01-03", "city": "Tokyo", "temperature": 4, "humidity": 40, "weather": "Sunny"},
    {"date": "2023-01-03", "city": "Osaka", "temperature": 7, "humidity": 45, "weather": "Sunny"},
]

# 東京の平均気温を計算
tokyo_temps = []
for item in data:
    if item["city"] == "Tokyo":
        tokyo_temps.append(item["temperature"])
tokyo_avg_temp = sum(tokyo_temps) / len(tokyo_temps)
print(f"東京の平均気温: {tokyo_avg_temp}℃")

# 大阪の平均気温を計算
osaka_temps = []
for item in data:
    if item["city"] == "Osaka":
        osaka_temps.append(item["temperature"])
osaka_avg_temp = sum(osaka_temps) / len(osaka_temps)
print(f"大阪の平均気温: {osaka_avg_temp}℃")

# 天気が「晴れ」の日の平均湿度を計算
sunny_humidity = []
for item in data:
    if item["weather"] == "Sunny":
        sunny_humidity.append(item["humidity"])
avg_sunny_humidity = sum(sunny_humidity) / len(sunny_humidity)
print(f"晴れの日の平均湿度: {avg_sunny_humidity}%")

# 最も暑かった日を見つける
hottest_day = None
max_temp = -100
for item in data:
    if item["temperature"] > max_temp:
        max_temp = item["temperature"]
        hottest_day = item
print(f"最も暑かった日: {hottest_day['date']}、都市: {hottest_day['city']}、気温: {hottest_day['temperature']}℃")