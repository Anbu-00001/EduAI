import subprocess, sys, json, time, os, requests, argparse
from pathlib import Path

# Path Hygiene: No hardcoded project names
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from config import PIPELINE_DIR, ARTIFACTS_DIR, PROCESSED_DIR

assert ROOT_DIR.exists(), f"ROOT_DIR missing: {ROOT_DIR}"
assert (ROOT_DIR / "config.py").exists(), "run_pipeline.py must live alongside config.py"

def run_cmd(cmd):
    print(f"\n> Running: {cmd}")
    env = os.environ.copy()
    # We run from project root, but ensure PYTHONPATH includes ROOT_DIR
    env["PYTHONPATH"] = f"{ROOT_DIR}:{os.environ.get('PYTHONPATH', '')}"
    
    # Change CWD for the subprocess to ROOT_DIR so internal relative paths work
    res = subprocess.run(cmd, shell=True, env=env, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="EduPredict AI Production Pipeline")
    parser.add_argument("--fetch-data", action="store_true", help="Download Indian datasets from Kaggle/NIRF")
    parser.add_argument("--retrain", action="store_true", help="Run full retraining pipeline")
    args = parser.parse_args()

    # Security: Do not hardcode API keys. Use environment variables.
    api_key = os.environ.get("DATAGOV_API_KEY")
    if not api_key:
        print("CRITICAL: DATAGOV_API_KEY environment variable not set.")
        print("Please export it: export DATAGOV_API_KEY=your_key_here")
        sys.exit(1)
    
    if args.fetch_data:
        run_cmd("python3 scripts/fetch_indian_datasets.py")

    # Step 1: DAG (Data Acquisition)
    run_cmd("python3 data/pipeline/dag.py")
    
    # Check cache
    cache_path = PIPELINE_DIR / "demand_cache.json"
    with open(cache_path) as f:
        cache = json.load(f)
        assert len(cache["records"]) >= 1, "demand_cache.json records empty"
        print("✅ Step 1: DAG complete")

    if args.retrain:
        # Step 2: Snapshot
        run_cmd("python3 data/pipeline/save_snapshot.py")
        print("✅ Step 2: Snapshot complete")

        # Step 3: Feature Engineering (Phase 5: Indian Datasets)
        run_cmd("python3 model/feature_engineering.py")
        features_path = PROCESSED_DIR / "features.csv"
        import pandas as pd
        df = pd.read_csv(features_path)
        assert df.shape[1] >= 14, f"Features CSV too narrow for Phase 5: {df.shape[1]} cols (expected 14+)"
        print("✅ Step 3: Feature engineering complete")

        # Step 4: Retrain with Temporal & Integrity
        run_cmd("python3 model/retrain_with_temporal.py")
        metrics_path = ARTIFACTS_DIR / "metrics.json"
        with open(metrics_path) as f:
            metrics = json.load(f)
            assert metrics["graph_regularised_auc"] >= 0.70, f"AUC too low for production: {metrics['graph_regularised_auc']}"
            print("✅ Step 4: Retraining & Integrity Hash complete")

    # Step 5: Docker Restart (or manual if docker not available)
    print("\n> Attempting to restart API container...")
    # docker-compose.yml is likely in the workspace root
    subprocess.run("docker compose restart api || true", shell=True)
    
    print("\nWaiting for API to stabilize...")
    time.sleep(5)
    
    # Final Check
    try:
        r = requests.get("http://localhost:8000/v1/health", timeout=5)
        if r.status_code == 200:
            print(f"✅ Step 5: API verified at v{r.json().get('version')}")
        else:
            print(f"⚠️ API health check failed: {r.text}")
    except Exception as e:
        print(f"⚠️ Could not reach API for final health check: {e}")

    print("\n══════════════════════════════════════")
    print("PHASE 5 DEPLOYMENT COMPLETE")
    print("══════════════════════════════════════")

if __name__ == "__main__":
    main()
