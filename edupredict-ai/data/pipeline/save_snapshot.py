import os
import json
import time
import shutil

def save_snapshot():
    cache_path = "data/pipeline/demand_cache.json"
    history_dir = "data/pipeline/history"
    
    if not os.path.exists(cache_path):
        raise FileNotFoundError(f"Cache file {cache_path} not found.")
    
    os.makedirs(history_dir, exist_ok=True)
    
    timestamp = int(time.time())
    snapshot_path = os.path.join(history_dir, f"snapshot_{timestamp}.json")
    
    shutil.copy2(cache_path, snapshot_path)
    
    snapshot_count = len([f for f in os.listdir(history_dir) if f.startswith("snapshot_")])
    print(f"Snapshot saved to {snapshot_path}")
    print(f"Total snapshots in history: {snapshot_count}")

if __name__ == "__main__":
    save_snapshot()
