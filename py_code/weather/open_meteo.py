#!/usr/bin/env python3
# /home/masuday/projects/takao35/py_code/weather/open_meteo.py

import requests
import traceback
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, List, Optional

LAT, LON = 35.624652, 139.242783
TIMEZONE = "Asia/Tokyo"
OUT_DIR = Path("/home/masuday/projects/takao35/py_data/weather")
OUT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = (
    "https://api.open-meteo.com/v1/jma"
    f"?latitude={LAT}&longitude={LON}"
    "&hourly=temperature_2m,precipitation,precipitation_probability,"
    "wind_speed_10m,wind_direction_10m,weathercode"
    "&current_weather=true"
    f"&timezone={TIMEZONE}"
)

JST = timezone(timedelta(hours=9))

def wind_dir_to_text(deg: Optional[float]) -> str:
    if deg is None:
        return "—"
    dirs = ["北","北北東","北東","東北東","東","東南東","南東","南南東",
            "南","南南西","南西","西南西","西","西北西","北西","北北西"]
    try:
        i = int((float(deg) % 360) / 22.5 + 0.5) % 16
        return dirs[i]
    except Exception:
        return "—"

WMO_MAP = {
    0: ("☀️","快晴"), 1: ("🌤️","晴れ(一部雲)"), 2: ("⛅","晴れ時々くもり"), 3: ("☁️","くもり"),
    45: ("🌫️","霧"), 48: ("🌫️","霧(着氷)"),
    51: ("🌦️","霧雨(弱)"), 53: ("🌦️","霧雨(並)"), 55: ("🌦️","霧雨(強)"),
    56: ("🌧️","着氷霧雨(弱)"), 57: ("🌧️","着氷霧雨(強)"),
    61: ("🌧️","雨(弱)"), 63: ("🌧️","雨(並)"), 65: ("🌧️","雨(強)"),
    66: ("🌧️","みぞれ雨(弱)"), 67: ("🌧️","みぞれ雨(強)"),
    71: ("🌨️","雪(弱)"), 73: ("🌨️","雪(並)"), 75: ("🌨️","雪(強)"),
    77: ("🌨️","雪あられ"),
    80: ("🌦️","にわか雨(弱)"), 81: ("🌧️","にわか雨(並)"), 82: ("🌧️","にわか雨(強)"),
    85: ("🌨️","にわか雪(弱)"), 86: ("🌨️","にわか雪(強)"),
    95: ("⛈️","雷雨(弱〜並)"), 96: ("⛈️","雷雨(雹:弱)"), 99: ("⛈️","雷雨(雹:強)"),
}
def wmo_icon_text(code: Any):
    try:
        return WMO_MAP.get(int(code), ("❓", f"不明({code})"))
    except Exception:
        return ("❓", "不明")

def fmt(v: Any, unit: str = "", nd: int = 1) -> str:
    try:
        return f"{round(float(v), nd)}{unit}"
    except Exception:
        return "—"

def parse_hour_to_naive_jst(s: Any) -> Optional[datetime]:
    if not isinstance(s, str):
        return None
    try:
        if s.endswith("Z") or "+" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST)
            return dt.replace(tzinfo=None)
        return datetime.fromisoformat(s)
    except Exception:
        return None

def index_from_now(times_iso: List[str]) -> int:
    now_naive = datetime.now(JST).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    best_i, best_d = 0, float("inf")
    for i, s in enumerate(times_iso):
        t = parse_hour_to_naive_jst(s)
        if t is None:
            continue
        d = abs((t - now_naive).total_seconds())
        if d < best_d:
            best_d, best_i = d, i
    return best_i

try:
    r = requests.get(API_URL, timeout=20)
    r.raise_for_status()
    data = r.json()

    # ======= 現在 =======
    cur = data.get("current_weather") or {}
    cur_icon, cur_text = wmo_icon_text(cur.get("weathercode"))
    t_iso = cur.get("time")
    if isinstance(t_iso, str):
        if t_iso.endswith("Z") or "+" in t_iso:
            obs_dt = datetime.fromisoformat(t_iso.replace("Z", "+00:00")).astimezone(JST)
        else:
            obs_dt = datetime.fromisoformat(t_iso).replace(tzinfo=JST)
    else:
        obs_dt = datetime.now(JST)
    obs_str = obs_dt.strftime("%H:%M時点")

    html_cur = f"""
    <html><head><meta charset="utf-8"><title>高尾山付近の天気</title>
    <style>
      body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif;margin:16px;color:#222;}}
      h2 small{{font-size:.7em;color:#666;margin-left:.5em;}}
      table{{border-collapse: collapse;width: 100%;table-layout: fixed;   /* 均等割り */}}
      th,td {{border: 1px solid #ddd;padding: 8px;text-align: center;word-break: keep-all;}}
    </style>
    </head><body>
    <h2>高尾山付近の天気 <small>{obs_str}</small></h2>
    <table>
      <tr><th>天気</th><th>気温</th><th>風速</th><th>風向</th><th>降水量</th></tr>
      <tr>
        <td>{cur_icon} {cur_text}</td>
        <td>{fmt(cur.get('temperature'),'℃')}</td>
        <td>{fmt(cur.get('windspeed'),'m/s')}</td>
        <td>{wind_dir_to_text(cur.get('winddirection'))}</td>
        <td>{fmt(cur.get('precipitation'),'mm')}</td>
      </tr>
    </table>
    <small>Weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a></small>
    </body></html>
    """
    (OUT_DIR/"takao_current.html").write_text(html_cur, encoding="utf-8")

    # JSON（現在）
    current_json = {
        "title": "高尾山付近の天気",
        "observed_at": obs_dt.isoformat(),
        "coord": {"lat": LAT, "lon": LON},
        "source": "open-meteo:jma",
        "current": {
            "weathercode": cur.get("weathercode"),
            "weather_text": cur_text,
            "weather_icon": cur_icon,
            "temperature_c": cur.get("temperature"),
            "wind_speed_ms": cur.get("windspeed"),
            "wind_dir_deg": cur.get("winddirection"),
            "wind_dir_text": wind_dir_to_text(cur.get("winddirection")),
            "precip_mm": cur.get("precipitation"),
        }
    }
    (OUT_DIR/"takao_current.json").write_text(
        json.dumps(current_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ======= hourly =======
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    t2m   = hourly.get("temperature_2m") or []
    prec  = hourly.get("precipitation") or []
    pop   = hourly.get("precipitation_probability") or []
    wspd  = hourly.get("wind_speed_10m") or []
    wdir  = hourly.get("wind_direction_10m") or []
    wcode = hourly.get("weathercode") or []

    def safe(arr: Optional[List[Any]], i: int, default=None):
        try:
            return arr[i]
        except Exception:
            return default

    # ======= 今後2日（6時間ごと）— JSONの時刻をそのまま利用 =======
    base_idx = index_from_now(times)
    step_indices = [base_idx + 6*k for k in range(9) if base_idx + 6*k < len(times)]

    th_cells, row_icon, row_text, row_t2m, row_wspd, row_wdir, row_prec, row_pop1h = ([] for _ in range(8))
    cols_json = []

    for j, idx in enumerate(step_indices):
        dt_naive = parse_hour_to_naive_jst(times[idx])
        tlabel = dt_naive.strftime("%-m/%-d %H:%M") if dt_naive else "—"
        th_cells.append(f"<th>{'現在' if j==0 else tlabel}</th>")
        icon, text = wmo_icon_text(safe(wcode, idx))
        row_icon.append(f"<td>{icon}</td>")
        row_text.append(f"<td>{text}</td>")
        row_t2m.append(f"<td>{fmt(safe(t2m, idx),'℃')}</td>")
        row_wspd.append(f"<td>{fmt(safe(wspd, idx),'m/s')}</td>")
        row_wdir.append(f"<td>{wind_dir_to_text(safe(wdir, idx))}</td>")
        row_prec.append(f"<td>{fmt(safe(prec, idx),'mm/h')}</td>")
        row_pop1h.append(f"<td>{fmt(safe(pop, idx+1),'%')}</td>")

        cols_json.append({
            "time_iso": times[idx],
            "label": ("現在" if j==0 else tlabel),
            "weathercode": safe(wcode, idx),
            "weather_text": text,
            "weather_icon": icon,
            "temperature_c": safe(t2m, idx),
            "wind_speed_ms": safe(wspd, idx),
            "wind_dir_deg": safe(wdir, idx),
            "wind_dir_text": wind_dir_to_text(safe(wdir, idx)),
            "precip_mmph": safe(prec, idx),
            "pop_next1h_pct": safe(pop, idx+1),
        })

    updated_caption = obs_dt.strftime("%H:%M") + "時点"

    html_2days = f"""
    <html><head><meta charset="utf-8"><title>今後2日の天気（6時間ごと）</title>
    <style>
      body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif;margin:16px;color:#222;}}
      h2 small{{font-size:.7em;color:#666;margin-left:.5em;}}
      table{{border-collapse:collapse;width:100%;table-layout:fixed;margin-top:8px;}}
      th,td{{border:1px solid #ddd;padding:8px;text-align:center;word-break:keep-all;}}
      th{{background:#f7f7f7;}}
    </style>
    </head><body>
      <h2>高尾山付近の天気（今後2日・6時間ごと） <small>{updated_caption}</small></h2>
      <table>
        <tr><th></th>{''.join(th_cells)}</tr>
        <tr><th>天気（アイコン）</th>{''.join(row_icon)}</tr>
        <tr><th>天気（文字）</th>{''.join(row_text)}</tr>
        <tr><th>気温</th>{''.join(row_t2m)}</tr>
        <tr><th>風速</th>{''.join(row_wspd)}</tr>
        <tr><th>風向</th>{''.join(row_wdir)}</tr>
        <tr><th>降水量</th>{''.join(row_prec)}</tr>
        <tr><th>降水確率（1時間後）</th>{''.join(row_pop1h)}</tr>
      </table>
      <small>Weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a></small>
    </body></html>
    """
    (OUT_DIR/"takao_2days.html").write_text(html_2days, encoding="utf-8")

    # JSON（2日・6時間ごと）
    two_days_json = {
        "title": "高尾山付近の天気（今後2日・6時間ごと）",
        "updated_at": obs_dt.isoformat(),
        "coord": {"lat": LAT, "lon": LON},
        "source": "open-meteo:jma",
        "columns": cols_json
    }
    (OUT_DIR/"takao_2days.json").write_text(
        json.dumps(two_days_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ======= 今日の天気（毎時） =======
    today_rows = []
    today_json_rows = []
    for i, s in enumerate(times):
        dt_naive = parse_hour_to_naive_jst(s)
        if dt_naive is None:
            continue
        if dt_naive.date() != datetime.now(JST).date():
            continue
        icon, text = wmo_icon_text(safe(wcode, i))
        today_rows.append(
            f"<tr>"
            f"<td>{dt_naive.strftime('%-m/%-d %H:%M')}</td>"
            f"<td>{icon}</td>"
            f"<td>{text}</td>"
            f"<td>{fmt(safe(t2m, i),'℃')}</td>"
            f"<td>{fmt(safe(wspd, i),'m/s')}</td>"
            f"<td>{wind_dir_to_text(safe(wdir, i))}</td>"
            f"<td>{fmt(safe(prec, i),'mm/h')}</td>"
            f"<td>{fmt(safe(pop, i+1),'%')}</td>"
            f"</tr>"
        )
        today_json_rows.append({
            "time_iso": s,
            "weathercode": safe(wcode, i),
            "weather_text": text,
            "weather_icon": icon,
            "temperature_c": safe(t2m, i),
            "wind_speed_ms": safe(wspd, i),
            "wind_dir_deg": safe(wdir, i),
            "wind_dir_text": wind_dir_to_text(safe(wdir, i)),
            "precip_mmph": safe(prec, i),
            "pop_next1h_pct": safe(pop, i+1),
        })

    html_today = f"""
    <html><head><meta charset="utf-8"><title>今日の天気（毎時）</title>
    <style>
      body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif;margin:16px;color:#222;}}
      h2 small{{font-size:.7em;color:#666;margin-left:.5em;}}
      table{{border-collapse:collapse;width:100%;table-layout:fixed;margin-top:8px;}}
      th,td{{border:1px solid #ddd;padding:8px;text-align:center;word-break:keep-all;}}
      th{{background:#f7f7f7;}}
    </style>
    </head><body>
      <h2>高尾山付近の天気（今日・毎時） <small>{updated_caption}</small></h2>
      <table>
        <tr>
          <th>時刻</th><th>天気(アイコン)</th><th>天気</th>
          <th>気温</th><th>風速</th><th>風向</th><th>降水量</th><th>降水確率（1時間後）</th>
        </tr>
        {''.join(today_rows) if today_rows else '<tr><td colspan="8">本日のデータがありません</td></tr>'}
      </table>
      <small>Weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a></small>
    </body></html>
    """
    (OUT_DIR/"takao_today.html").write_text(html_today, encoding="utf-8")

    # JSON（今日・毎時）
    today_json = {
        "title": "高尾山付近の天気（今日・毎時）",
        "updated_at": obs_dt.isoformat(),
        "coord": {"lat": LAT, "lon": LON},
        "source": "open-meteo:jma",
        "rows": today_json_rows
    }
    (OUT_DIR/"takao_today.json").write_text(
        json.dumps(today_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("更新OK:", obs_str)

except Exception as e:
    print("エラー:", e)
    traceback.print_exc()