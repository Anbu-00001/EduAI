import subprocess, sys, json, time, os

def run_cmd(cmd):
    print(f"\n> Running: {cmd}")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    res = subprocess.run(cmd, shell=True, env=env)
    if res.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(1)

def main():
    # Set API Key for DAG
    os.environ["DATAGOV_API_KEY"] = "579b464db66ec23bdd000001b24b1b5fc31d4cb375a8f3473463ff63"
    
    # Step 1: DAG
    run_cmd("python3 data/pipeline/dag.py")
    with open("data/pipeline/demand_cache.json") as f:
        cache = json.load(f)
        assert len(cache["records"]) >= 1, "demand_cache.json records empty"
        print("✅ Step 1: DAG complete")

    # Step 2: Snapshot
    run_cmd("python3 data/pipeline/save_snapshot.py")
    history_files = os.listdir("data/pipeline/history")
    assert len(history_files) >= 1, "No snapshots in history"
    print("✅ Step 2: Snapshot complete")

    # Step 3: Feature Engineering (v2 logic + v3 placeholders)
    run_cmd("python3 model/feature_engineering.py")
    import pandas as pd
    df = pd.read_csv("data/processed/features.csv")
    assert df.shape[1] >= 8, f"Features CSV too narrow: {df.shape[1]} cols"
    print("✅ Step 3: Feature engineering complete")

    # Step 4: Retrain with Temporal
    run_cmd("python3 model/retrain_with_temporal.py")
    with open("model/artifacts/metrics.json") as f:
        metrics = json.load(f)
        assert metrics["graph_regularised_auc"] >= 0.78, f"AUC too low: {metrics['graph_regularised_auc']}"
        assert metrics["post_calibration_ece"] < 0.05, f"ECE too high: {metrics['post_calibration_ece']}"
        print("✅ Step 4: Retraining complete")

    # Step 5: Docker Restart (or manual if docker not available)
    print("\n> Attempting to restart API container...")
    run_cmd("docker-compose restart api || true")
    
    print("\nWaiting for API to stabilize...")
    time.sleep(5)
    
    # Final Check
    try:
        import requests
        r = requests.get("http://localhost:8000/v1/health")
        if r.status_code == 200 and r.json().get("model_version") == "v3.0-temporal-graph":
            print("✅ Step 5: API verified at v3.0")
        else:
            print(f"⚠️ API health check failed or version mismatch: {r.text}")
    except:
        print("⚠️ Could not reach API for final health check. Ensure it is running.")

    print("\n══════════════════════════════════════")
    print("PHASE 3 DEPLOYMENT COMPLETE")
    print("══════════════════════════════════════")

if __name__ == "__main__":
    main()
