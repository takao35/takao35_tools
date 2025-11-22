import os
import json
import csv
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict


@dataclass
class StationInfo:
    name: str
    use_type: str  # deperture, transit, destination
    departuret_time: Optional[str] = None
    deptarture_platform: Optional[int] = None
    arrival_time: Optional[str] = None
    arrival_platform: Optional[int] = None


@dataclass
class RouteInfo:
    train_type: str  # Keio_Liner, Express, Local
    day_type: str  # weekday, holiday
    origin_station_info: StationInfo
    terminal_station_info: StationInfo
    transits: Optional[List[StationInfo]] = None


def to_dt(s: Optional[str]) -> Optional[datetime]:
    """ISO8601文字列→datetime（失敗/NoneならNone）。Zにも対応。"""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def ensure_list_of_dicts(x):
    """stop_stations列を list[dict] に正規化。文字列ならJSONデコード。失敗時は []。"""
    if x is None:
        return []
    if isinstance(x, str):
        try:
            x = json.loads(x)
        except Exception:
            return []
    if isinstance(x, list):
        return [d for d in x if isinstance(d, dict)]
    return []


def parse_json(val):
    """
    CSVの stop_stations は "[{""station"": ""新宿"", ...}]" のように
    二重の二重引用符になることがある。これを確実に Python オブジェクトにする。
    """
    if isinstance(val, (list, dict)):
        return val
    if val is None:
        return None
    if not isinstance(val, str):
        return None

    s = val.strip()
    # まずは素直に
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 次に "" -> " の置換で再トライ
    try:
        fixed = s.replace('""', '"')
        return json.loads(fixed)
    except Exception:
        pass

    # 最後の手段：literal_eval（やや緩め）
    try:
        import ast

        return ast.literal_eval(s)
    except Exception:
        return None


today_str = datetime.now().strftime("%Y%m%d")
day_type = ["weekday", "holiday"]
data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "py_data", "train")
output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "py_data", "train", "publish")
os.makedirs(output_dir, exist_ok=True)


def get_next_train_kitano_to_takao3(target_time: str, d_type) -> Optional[Dict]:
    fk_name = f"{today_str}_{d_type}_kitano_to_takao.csv"
    fk_path = os.path.join(data_dir, fk_name)
    if not os.path.exists(fk_path):
        return None

    df_k = pd.read_csv(fk_path)
    if df_k.empty:
        return None

    df_k["stop_stations"] = df_k["stop_stations"].apply(ensure_list_of_dicts)

    result = None
    best_arr_dt = None
    target_dt = to_dt(target_time)

    for _, row in df_k.iterrows():
        dep_dt = to_dt(row.get("time_iso"))
        if not dep_dt:
            continue
        if target_dt and dep_dt < target_dt:
            continue

        # 高尾山口の到着時刻を拾う
        takao_arr = None
        for st in row["stop_stations"]:
            if st.get("station") == "高尾山口":
                takao_arr = st.get("time")
                break

        arr_dt = to_dt(takao_arr)
        if not arr_dt:
            continue

        if best_arr_dt is None or arr_dt < best_arr_dt:
            best_arr_dt = arr_dt
            result = {
                "departure_time": row.get("time_iso"),
                "arrival_time": takao_arr,
                "train_type": row.get("train_type"),
                "operation_id": row.get("operation_id"),
                "platform": row.get("platform"),
            }
    return result


def get_next_train_kitano_to_shinjuku(target_time: str, d_type) -> Optional[Dict]:
    fk_name = f"{today_str}_{d_type}_kitano_to_shinjuku.csv"
    fk_path = os.path.join(data_dir, fk_name)
    if not os.path.exists(fk_path):
        return None

    df_k = pd.read_csv(fk_path)
    if df_k.empty:
        return None

    df_k["stop_stations"] = df_k["stop_stations"].apply(ensure_list_of_dicts)

    result = None
    best_arr_dt = None
    target_dt = to_dt(target_time)

    for _, row in df_k.iterrows():
        dep_dt = to_dt(row.get("time_iso"))
        if not dep_dt:
            continue
        if target_dt and dep_dt < target_dt:
            continue

        shinjuku_arr = None
        for st in row["stop_stations"]:
            if st.get("station") == "新宿":
                shinjuku_arr = st.get("time")
                break

        arr_dt = to_dt(shinjuku_arr)
        if not arr_dt:
            continue

        if best_arr_dt is None or arr_dt < best_arr_dt:
            best_arr_dt = arr_dt
            result = {
                "departure_time": row.get("time_iso"),
                "arrival_time": shinjuku_arr,
                "train_type": row.get("train_type"),
                "operation_id": row.get("operation_id"),
                "platform": row.get("platform"),
            }
    return result


def station_info_from_dict(data: dict) -> StationInfo:
    return StationInfo(**data)


def takao3_to_shinjuku():
    all_routes = []
    for d_type in day_type:
        fs_name = f"{today_str}_{d_type}_takao_to_up.csv"
        fs_path = os.path.join(data_dir, fs_name)
        if not os.path.exists(fs_path):
            continue

        df_s = pd.read_csv(fs_path)
        if df_s.empty:
            continue

        df_s["stop_stations"] = df_s["stop_stations"].apply(ensure_list_of_dicts)

        for _, row in df_s.iterrows():
            origin = StationInfo(
                name="高尾山口",
                use_type="deperture",
                departuret_time=row.get("departure_dt"),
                deptarture_platform=row.get("platform"),
            )

            shinjuku_arr = None
            kitano_arr = None
            for st in row["stop_stations"]:
                if st.get("station") == "新宿":
                    shinjuku_arr = st.get("time")
                    break
                if st.get("station") == "北野":
                    kitano_arr = st.get("time")

            if shinjuku_arr:
                # 直通
                terminal = StationInfo(
                    name="新宿",
                    use_type="destination",
                    arrival_time=shinjuku_arr,
                )
                transits = None
            else:
                # 北野乗換
                if not kitano_arr:
                    continue
                tran_data = get_next_train_kitano_to_shinjuku(kitano_arr, d_type)
                if not tran_data:
                    continue
                transits = [
                    StationInfo(
                        name="北野",
                        use_type="transit",
                        arrival_time=kitano_arr,
                        departuret_time=tran_data.get("departure_time"),
                        deptarture_platform=tran_data.get("platform"),
                    )
                ]
                terminal = StationInfo(
                    name="新宿",
                    use_type="destination",
                    arrival_time=tran_data.get("arrival_time"),
                )

            route_info = RouteInfo(
                train_type=str(row.get("train_type") or ""),
                day_type=d_type,
                origin_station_info=origin,
                terminal_station_info=terminal,
                transits=transits,
            )
            all_routes.append(route_info)

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{today_str}_takao3_to_shinjuku.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([asdict(route) for route in all_routes],
                f, ensure_ascii=False, indent=4)
    print(f"データは {output_file} に保存されました。")


def shinjuku_to_takao3():
    all_routes = []

    # --- 直通 ---
    for d_type in day_type:
        fs_name = f"{today_str}_{d_type}_shinjuku_to_takao_direct.csv"
        fs_path = os.path.join(data_dir, fs_name)
        if not os.path.exists(fs_path):
            continue

        df_s = pd.read_csv(fs_path)
        if df_s.empty:
            continue

        df_s["stop_stations"] = df_s["stop_stations"].apply(ensure_list_of_dicts)

        for _, row in df_s.iterrows():
            origin = StationInfo(
                name="新宿",
                use_type="deperture",
                departuret_time=row.get("departure_dt"),
                deptarture_platform=row.get("platform"),
            )
            # 高尾山口の到着時刻
            takao_arr = None
            for st in row["stop_stations"]:
                if st.get("station") == "高尾山口":
                    takao_arr = st.get("time")
                    break

            terminal = StationInfo(
                name="高尾山口",
                use_type="destination",
                arrival_time=takao_arr,
            )

            route_info = RouteInfo(
                train_type=str(row.get("train_type") or ""),
                day_type=d_type,
                origin_station_info=origin,
                terminal_station_info=terminal,
                transits=None,
            )
            all_routes.append(route_info)

    # --- 北野乗換（新宿→京王八王子 特急 + 北野→高尾山口）---
    for d_type in day_type:
        fk_name = f"{today_str}_{d_type}_shinjuku_to_keiohachioji.csv"  # ← day_type[0] ではなく d_type
        fk_path = os.path.join(data_dir, fk_name)
        if not os.path.exists(fk_path):
            continue

        df_k = pd.read_csv(fk_path)
        if df_k.empty:
            continue

        df_k["stop_stations"] = df_k["stop_stations"].apply(ensure_list_of_dicts)

        for _, row in df_k.iterrows():
            origin = StationInfo(
                name="新宿",
                use_type="deperture",
                departuret_time=row.get("departure_dt"),
                deptarture_platform=row.get("platform"),
            )

            # 北野到着時刻を拾う
            kitano_arr = None
            for st in row["stop_stations"]:
                if st.get("station") == "北野":
                    kitano_arr = st.get("time")
                    break
            if not kitano_arr:
                continue  # 乗換基準時刻が取れなければスキップ

            tran_data = get_next_train_kitano_to_takao3(kitano_arr, d_type)
            if not tran_data:
                continue

            transit_info = StationInfo(
                name="北野",
                use_type="transit",
                arrival_time=kitano_arr,
                departuret_time=tran_data.get("departure_time"),
                deptarture_platform=tran_data.get("platform"),
            )
            terminal = StationInfo(
                name="高尾山口",
                use_type="destination",
                arrival_time=tran_data.get("arrival_time"),
            )

            route_info = RouteInfo(
                day_type=d_type,
                origin_station_info=origin,
                terminal_station_info=terminal,
                transits=[transit_info],
                train_type=str(row.get("train_type") or ""),
            )
            all_routes.append(route_info)

    # JSON保存（ディレクトリが無ければ作成）
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{today_str}_shinjuku_to_takao3.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([asdict(route) for route in all_routes],
                f, ensure_ascii=False, indent=4)
    print(f"データは {output_file} に保存されました。")


# 実行例
if __name__ == "__main__":
    shinjuku_to_takao3()
    takao3_to_shinjuku()
