import pandas as pd
import os

files = ['placementdata.csv', 'Placement.csv', 'loan_approval_dataset.csv', 'loan.csv', 'Scorecard.csv']
base_path = "edupredict-ai/data/raw/"

for f in files:
    path = os.path.join(base_path, f)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, nrows=5)
            print(f"\nFILE: {f}")
            print(f"COLUMNS: {df.columns.tolist()}")
            print(f"SHAPE: {df.shape}")
        except Exception as e:
            print(f"ERROR reading {f}: {e}")
    else:
        print(f"FILE NOT FOUND: {f}")
