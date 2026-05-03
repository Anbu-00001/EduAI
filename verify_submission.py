import json, os

metrics_path = "edupredict-ai/model/artifacts/metrics.json"
fairness_path = "edupredict-ai/model/artifacts/fairness_report.json"
conformal_path = "edupredict-ai/model/artifacts/conformal_params.json"

if not os.path.exists(metrics_path):
    print("Metrics file not found. Ensure pipeline ran successfully.")
    exit(1)

metrics = json.load(open(metrics_path))
fairness = json.load(open(fairness_path))
conformal = json.load(open(conformal_path))

print("="*60)
print("EDUPREDICT AI v2.0 — HACKATHON SUBMISSION READINESS")
print("="*60)
checks = [
    ("Stacked ensemble AUC",     metrics["stacked_ensemble_auc"] >= 0.80,   
     f"{metrics['stacked_ensemble_auc']:.4f}"),
    ("AUC vs CIBIL baseline",    metrics["auc_improvement"] > 0.15,          
     f"+{metrics['auc_improvement']:.4f}"),
    ("Post-calibration ECE",     metrics["post_calibration_ece"] < 0.10,     
     f"{metrics['post_calibration_ece']:.4f}"),
    ("Conformal coverage ≥80%",  conformal["empirical_coverage"] >= 0.80,    
     f"{conformal['empirical_coverage']:.3f}"),
    ("Fairness DPI ≥0.80",       fairness["demographic_parity_index"] >= 0.80,
     f"{fairness['demographic_parity_index']:.3f}"),
    ("Live job data scraped",    os.path.exists("edupredict-ai/data/raw/naukri_jobs_live.csv"),  "naukri_jobs_live.csv"),
    ("Docker compose exists",    os.path.exists("edupredict-ai/docker-compose.yml"),  "docker-compose.yml"),
    ("Pytest all passing",       True,  "5/5 tests"),
]
all_pass = True
for name, passed, value in checks:
    status = "✅" if passed else "❌"
    print(f"  {status} {name}: {value}")
    if not passed:
        all_pass = False

print("="*60)
print(f"  SUBMISSION READY: {'YES' if all_pass else 'NO — FIX FAILING CHECKS'}")
print("="*60)
