import pandas as pd
from pathlib import Path

def convert_seasonal_data():
    in_dir = Path("data_local/raw_scrapes")
    out_dir = Path("data/rankings")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    positions = ["QB", "RB", "WR", "TE", "K"]
    for pos in positions:
        # Our local directory has {POS}_2025_seasonal.csv
        # Let's glob everything and concatenate if there are multiple years, or just read the _seasonal
        csv_files = list(in_dir.glob(f"{pos}_*_seasonal.csv"))
        if not csv_files:
            continue
            
        dfs = []
        for f in csv_files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception as e:
                print(f"Skipping {f}: {e}")
                
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            out_file = out_dir / f"{pos}_seasonal.parquet"
            combined.to_parquet(out_file, index=False)
            print(f"Successfully wrote {out_file}")

if __name__ == "__main__":
    convert_seasonal_data()
