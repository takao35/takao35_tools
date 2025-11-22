from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class StationInfo:
    name: str
    use_type: str   # deperture, transit, destination
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