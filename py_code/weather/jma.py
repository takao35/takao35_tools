#!/usr/bin/env python3
import os, json, re, requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from lxml import etree


JMA = "https://www.jma.go.jp"
STN = "44112"  # 八王子

UA = {"User-Agent": "TakaoApp/1.0 (+https://takaosan-go.jp)"}
OUT_DIR = Path("/home/masuday/projects/takao35/py_data/weather")

def get_latest_point_json_url():
    # 例: "2025-09-07T12:10:00+09:00"
    latest = requests.get(f"{JMA}/bosai/amedas/data/latest_time.txt", headers=UA, timeout=15).text.strip()
    print(f"latest_time:{latest}")
    # 日付と3時間ブロック（00,03,...,21）を作る
    dt = datetime.fromisoformat(latest.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=9)))
    ymd = dt.strftime("%Y%m%d")
    h3  = f"{(dt.hour//3)*3:02d}"
    return f"{JMA}/bosai/amedas/data/point/{STN}/{ymd}_{h3}.json", latest

def load_point_series(url):
    r = requests.get(url, headers=UA, timeout=20); r.raise_for_status()
    return r.json()  # { "temp":[{ "time":"...", "value":..}, ...], "precipitation1h":[...], ... } の形式

def pick_latest(series, key):
    """point形式: 時刻キーで降順→ node[key] が [value, flag] なら value を返す"""
    # series は {"YYYYmmddHHMMSS": {"temp": [v, q], ...}, ...}
    if not isinstance(series, dict):
        return None, None
    for ts in sorted(series.keys(), reverse=True):  # 新しい順
        node = series.get(ts) or {}
        arr = node.get(key)
        if isinstance(arr, list) and arr:
            val = arr[0]
            if val is not None:
                return val, ts
    return None, None

def infer_now_weather(p10, p1h, sun10, sun1h):
    # 1) 雨
    if (p10 or 0) > 0:
        return "雨"
    if (p1h or 0) >= 1.0:
        return "本降りの雨"
    # 2) 日差し
    s10 = sun10 or 0
    if s10 >= 5:
        return "晴れ間あり"
    if 1 <= s10 < 5:
        return "薄日"
    # 3) デフォルト
    return "くもり寄り"


def main_current():
    url, latest_ts = get_latest_point_json_url()
    series = load_point_series(url)
    print(f"Loaded AMeDAS data {series}")
    # ・・・AMeDASのseries取得後：
    temp, _   = pick_latest(series, "temp")
    rain10,_  = pick_latest(series, "precipitation10m")
    rain1h,_  = pick_latest(series, "precipitation1h")
    sun10,_   = pick_latest(series, "sun10m")
    sun1h,_   = pick_latest(series, "sun1h")
    wind,_    = pick_latest(series, "wind")
    humi,_    = pick_latest(series, "humidity")
    wdir,_     = pick_latest(series, "windDirection")
    now_sky   = infer_now_weather(rain10, rain1h, sun10, sun1h)

    # まとめ（欠測は None のまま許容）
    obs = {
        "station": "八王子(AMeDAS 44112)",
        "latest_source_time": latest_ts,
        "temperature_c": temp,
        "precip_10m_mm": rain10,
        "precip_1h_mm": rain1h,
        "sun_10m_min": sun10,
        "sun_1h_min": sun1h,
        "wind_ms": wind,
        "wind_dir_deg": wdir,
        "humidity_pct": humi,
        "now_sky_guess": now_sky,  # ← これをブログやアプリの“現在”欄に
        "note": "気象庁アメダス実測 / 欠測はNone"
    }

    # 出力
    out_json = os.environ.get("OUT_JSON", f"{OUT_DIR}/amedas_44112.json")
    out_html = os.environ.get("OUT_HTML", f"{OUT_DIR}/amedas_44112.html")
    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(obs, f, ensure_ascii=False, indent=2)

    # ブログ用（貼り付け部品）
    def fmt(v, unit=""):
        return "—" if v is None else f"{v}{unit}"
    html = f"""<!-- AMeDAS(44112) snippet -->
<div class="takao-amedas" style="border:1px solid #ddd;border-radius:12px;padding:12px;">
  <div style="font-weight:600;margin-bottom:6px;">八王子の実測（AMeDAS 44112）</div>
  <div>気温: {fmt(temp, "℃")}　1時間降水: {fmt(rain1h, "mm")}　風: {fmt(wind, "m/s")}　湿度: {fmt(humi, "%")}</div>
  <div style="font-size:12px;color:#666;margin-top:6px;">出典: 気象庁 アメダス（{latest_ts} 時点の最新時刻束）</div>
</div>"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)


REGULAR = "http://xml.kishou.go.jp/xmlpull/regular.xml"

def fetch_forecast_xml():
    feed = requests.get(REGULAR, headers=UA, timeout=15).text
    urls = re.findall(r"https?://[^\s\"']+VPFD[^\s\"']+\.xml", feed)
    if not urls:
        raise RuntimeError("予報URLが見つからない")
    return requests.get(urls[0], headers=UA, timeout=15).content

def parse_forecast(xml_bytes, area_code="130015"):
    ns = {
        "jmx_ib": "http://xml.kishou.go.jp/jmaxml1/informationBasis1/",
        "jmx_mm": "http://xml.kishou.go.jp/jmaxml1/meteorology1/",
    }
    root = etree.fromstring(xml_bytes)
    for area in root.findall(".//jmx_mm:Area", namespaces=ns):
        code = area.get("code")
        if code != area_code:
            continue
        summaries = area.findall(".//jmx_mm:Weather", namespaces=ns)
        tmax_nodes = area.findall(".//jmx_mm:Temperature[@type='最高']", namespaces=ns)
        tmin_nodes = area.findall(".//jmx_mm:Temperature[@type='最低']", namespaces=ns)
        pops = area.findall(".//jmx_mm:ProbabilityOfPrecipitation", namespaces=ns)

        def safe(node_list, idx):
            return node_list[idx].text if len(node_list) > idx else None

        tomorrow = {
            "summary": safe(summaries, 0),
            "tmax": safe(tmax_nodes, 0),
            "tmin": safe(tmin_nodes, 0),
            "precipProb": {"am": None, "pm": None},
        }
        day_after = {
            "summary": safe(summaries, 1),
            "tmax": safe(tmax_nodes, 1),
            "tmin": safe(tmin_nodes, 1),
            "precipProb": {"am": None, "pm": None},
        }

        for p in pops:
            period = p.get("period") or ""
            if "午前" in period and tomorrow["precipProb"]["am"] is None:
                tomorrow["precipProb"]["am"] = p.text
            elif "午後" in period and tomorrow["precipProb"]["pm"] is None:
                tomorrow["precipProb"]["pm"] = p.text

        return {"area": "多摩南部", "tomorrow": tomorrow, "day_after": day_after}
    return {}

if __name__ == "__main__":
    xml = fetch_forecast_xml()
    fc = parse_forecast(xml)
    print(fc)
    main_current()
