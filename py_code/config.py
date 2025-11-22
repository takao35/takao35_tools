# py_code/config.py
from pathlib import Path
import os

_THIS = Path(__file__).resolve()
CODE_DIR = _THIS.parent                    # .../py_code
PROJECT_ROOT = CODE_DIR.parent             # .../（プロジェクトルート）
ROOT_DIR = PROJECT_ROOT                    # 互換目的で残す

DATA_DIR = PROJECT_ROOT / "py_data"

# ランタイム(ロック/状態)の既定場所: env > 既定
RUNTIME_DIR = Path(os.getenv("REPP_RATE_STATE_DIR", PROJECT_ROOT / "var" / "rate"))

__all__ = ["PROJECT_ROOT", "ROOT_DIR", "CODE_DIR", "DATA_DIR", "RUNTIME_DIR"]