import requests
import json
import sys

def verify_live_api():
    print("--- LIVE API VERIFICATION ---")
    url = "http://localhost:8000/api/v1/rankings/qb?year=2025"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"FAIL: API returned status {response.status_code}")
            return False
            
        data = response.json()
        
        # Look for Josh Allen (Normalized key is player_name)
        allen = next((p for p in data if "Josh Allen" in p.get("player_name", "")), None)
        
        if not allen:
            print("FAIL: Josh Allen not found in live API response.")
            return False
            
        print(f"Player:       {allen.get('Player')}")
        print(f"FPTS (Total): {allen.get('fpts_ppr')}")
        print(f"Games (G):    {allen.get('G')}")
        print(f"Current Rank: {allen.get('Rank')}")
        
        # Expected from previous CSV audit: 385.10
        fpts = float(allen.get('fpts_ppr', 0))
        if abs(fpts - 385.1) < 0.2:
            print("\nRESULT: PASS - Live API is serving correct cumulative totals.")
            return True
        else:
            print(f"\nRESULT: FAIL - Discrepancy in live API. Expected 385.1, got {fpts}")
            return False
            
    except Exception as e:
        print(f"ERROR connecting to API: {e}")
        return False

if __name__ == "__main__":
    if verify_live_api():
        sys.exit(0)
    else:
        sys.exit(1)
