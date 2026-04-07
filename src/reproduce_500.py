import sys
from pathlib import Path

# Ensure 'src' is in sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import duckdb
from backend.data.query_engine import query_rankings

def test_reproduce():
    print("Testing query_rankings('qb', year=2025)...")
    try:
        data = query_rankings('qb', year=2025)
        print(f"SUCCESS: Got {len(data)} records")
        if data:
            print("First record keys:", data[0].keys())
    except Exception as e:
        print("FAILED with exception:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reproduce()
