"""Disposable, offline real FastAPI server for deterministic browser checks."""
import tempfile
from pathlib import Path
import uvicorn
from backend.config import Config
from backend.store import Store
from backend.trading import dataset
from backend.main import create_app


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="lmw-e2e-") as directory:
        path = str(Path(directory) / "browser.sqlite3")
        store = Store(path, "BHP.AX")
        for bar in dataset("yahoo-4-1")["bars"]:
            store.append("bar", {"start_ms":bar["time"]*1000, **{k:bar[k] for k in ("open","high","low","close","volume")}, "finalized":True},bar["end_ms"])
        store.close()
        uvicorn.run(create_app(Config(db_path=path), start_provider=False), host="127.0.0.1", port=8123, log_level="warning")
