import os
import subprocess
from pathlib import Path

def fetch():
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    print("=================================================================")
    print("EduPredict AI — Dataset Acquisition Tool")
    print("=================================================================\n")

    # 1. IEEE DataPort (Manual download usually, but we'll stub it)
    print("[S1] IEEE DataPort Engineering Graduate Dataset")
    print("     Manual Download Required: https://ieee-dataport.org/documents/engineering-graduate-employability-and-salary-dataset")
    print("     Place CSVs in: data/raw/ieee_indian_placement/\n")
    
    # 2. Kaggle: Indian Student Placement Dataset 2025
    print("[S2] Fetching Kaggle Indian Student Placement Dataset 2025...")
    try:
        subprocess.run([
            "kaggle", "datasets", "download", "-d", 
            "sakharebharat/indian-student-placement-dataset-2025", 
            "-p", str(raw_dir / "kaggle_indian_placement"), "--unzip"
        ], check=True)
        print("     ✅ S2 Complete")
    except Exception as e:
        print(f"     ❌ S2 Failed: {e}. Ensure kaggle CLI is installed and ~/.kaggle/kaggle.json exists.")
    
    # 3. NIRF Rankings Dataset
    print("\n[S3] Fetching NIRF Rankings Dataset...")
    try:
        subprocess.run([
            "kaggle", "datasets", "download", "-d", 
            "iitanshravan/nirf-rankings-dataset-20162025", 
            "-p", str(raw_dir / "nirf"), "--unzip"
        ], check=True)
        print("     ✅ S3 Complete")
    except Exception as e:
        print(f"     ❌ S3 Failed: {e}")

    print("\nNext Step: Run 'python run_pipeline.py --retrain' to build the model.")

if __name__ == "__main__":
    fetch()
