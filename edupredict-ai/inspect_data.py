import pandas as pd
import os

data_dir = "/home/anbu/25_class/Sem_4/EduAI/edupredict-ai/data/raw"
files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

for file in files:
    filepath = os.path.join(data_dir, file)
    print(f"\n--- Inspecting {file} ---")
    try:
        df = pd.read_csv(filepath, nrows=5)
        print("Columns:", df.columns.tolist())
        print("Dtypes:\n", df.dtypes)
        print("Shape (sample):", df.shape)
    except Exception as e:
        print(f"Error reading {file}: {e}")
