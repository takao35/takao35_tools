#!/usr/bin/env python3
import json
from pathlib import Path
from fs_client import post_news

CUR_JSON = Path("/home/masuday/projects/takao35/py_data/weather/takao_current.json")

def main():
    j = json.loads(CUR_JSON.read_text(encoding="utf-8"))
    word = j.get("current", {}).get("weather_text") or "—"
    post_news(
        "weather:now",
        title=f"現在の高尾山の天気：{word}",
        type_="weather",
        url="https://www.takaosan-go.jp/index.php/information/",   # ←あなたの天気ページ
        pin=1
    )
    print("publish weather: OK")

if __name__ == "__main__":
    main()