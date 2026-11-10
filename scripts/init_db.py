"""Run from repository root: .venv/bin/python -m scripts.init_db"""
from backend.config import Config
from backend.store import Store

if __name__ == "__main__":
    config = Config()
    store = Store(config.db_path,config.symbol)
    print(f"SQLite initialized: {config.db_path}; symbol={config.symbol}; events={store.count()}")
    store.close()
