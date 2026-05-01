"""
Development utility — inspect a dataset CSV.
Usage: python scripts/dev/inspect_dataset.py --file data/raw/placementdata.csv
"""
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

def main():
    parser = argparse.ArgumentParser(description="Inspect a dataset CSV file.")
    parser.add_argument("--file", required=True, help="Path to CSV, relative to project root")
    parser.add_argument("--rows", type=int, default=5, help="Number of sample rows to show")
    args = parser.parse_args()

    filepath = ROOT_DIR / args.file
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    import pandas as pd
    df = pd.read_csv(filepath, nrows=args.rows)
    print(f"\nFile:    {filepath}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Dtypes:\n{df.dtypes}")
    print(f"\nSample ({args.rows} rows):")
    print(df.to_string())

if __name__ == "__main__":
    main()
