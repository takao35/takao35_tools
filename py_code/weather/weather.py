import requests, json, datetime as dt

APPID = "dj00aiZpPUpMSFluM3NJOXpZTCZzPWNvbnN1bWVyc2VjcmV0Jng9NDU-"
lon, lat = 139.242783, 35.624652
url = ("https://map.yahooapis.jp/weather/V1/place"
       f"?coordinates={lon},{lat}&output=json&interval=10&past=1&appid={APPID}")

r = requests.get(url, timeout=10)
r.raise_for_status()
j = r.json()
info = j.get("ResultInfo")
print(info)   # {'Count': 1, 'Total': 1, 'Start': 1, 'Status': 200}
feat = j["Feature"]
print(feat)   # ['WeatherList', 'WeatherCodes', 'WeatherAreaCode']
area_code = feat["Property"].get("WeatherAreaCode")
series = [
    {
      "type": w["Type"],              # "observation" or "forecast"
      "time": w["Date"],              # "YYYYMMDDHHMI"
      "rainfall_mmph": float(w["Rainfall"])
    } for w in feat["Property"]["WeatherList"]["Weather"]
]

out = {
  "yolp_rain_nowcast": {
    "coordinates": {"lat": lat, "lon": lon},
    "weather_area_code": area_code,
    "series": series,
    "generated_at": dt.datetime.utcnow().isoformat()+"Z"
  }
}
print(json.dumps(out, ensure_ascii=False))