import os
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_symbol(value):
    value = value.upper().strip()
    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=\-]{0,19}", value):
        raise ValueError("SYMBOL must be a Yahoo symbol, 1–20 letters/digits . ^ = -")
    return value


@dataclass(frozen=True)
class Config:
    symbol: str = validate_symbol(os.getenv("SYMBOL", "BHP.AX"))
    db_path: str = os.getenv("DATABASE_PATH", str(ROOT / "data" / "market.sqlite3"))
    stale_seconds: int = 30
    max_attempts: int = 5
