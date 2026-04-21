import os
import sys
import re
from pathlib import Path

# V3 Standards Configuration
MANDATORY_TOKENS = ["#38bdf8", "#020617"] # Midnight Slate
REASONING_HEADERS = ["Null-Safety Strategy", "UI Token Compliance", "Verification Steps"]

def audit_data_integrity():
    print("Gate 1: Data Integrity Audit...")
    query_engine = Path("src/backend/data/query_engine.py")
    if not query_engine.exists():
        print("FAILED: backend/data/query_engine.py not found.")
        return False
    
    content = query_engine.read_text(encoding="utf-8")
    # Check for DuckDB NULLS LAST and Python None mapping
    if "None" in content and "NULLS LAST" in content:
        print("PASS: Null-Safety and NULLS LAST logic detected.")
        return True
    else:
        print("WARNING: Explicit Null-Safety patterns not confirmed in query_engine.")
        return False

def audit_midnight_slate():
    print("Gate 2: Midnight Slate UI Audit (Tailwind v4+ Support)...")
    
    # Check for tailwind.config.* (Legacy) or index.css (Tailwind v4 @theme)
    search_paths = [
        Path("frontend/nflstats-pro-ui/src/styles/global.css"),
        Path("frontend/nflstats-pro-ui/src/index.css"),
        Path("tailwind.config.js"),
        Path("frontend/tailwind.config.js")
    ]
    
    found_tokens = False
    for path in search_paths:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            # In Tailwind 4, we look for @theme block or custom properties
            if any(token in content for token in MANDATORY_TOKENS):
                print(f"PASS: Tokens validated in {path}")
                found_tokens = True
                break
            elif "primary: #38bdf8" in content.lower():
                print(f"PASS: Primary color found in {path}")
                found_tokens = True
                break
                
    if not found_tokens:
        print(f"FAILED: Mandatory tokens ({MANDATORY_TOKENS}) missing from UI config files.")
        return False
    return True

def audit_protocol():
    print("Gate 3: Protocol Compliance Audit...")
    reasoning_path = Path("swarm/reasoning.md")
    if not reasoning_path.exists():
        print("FAILED: swarm/reasoning.md not found.")
        return False
    
    content = reasoning_path.read_text(encoding="utf-8")
    # Check for headers ignoring markdown level and whitespace
    missing = []
    for header in REASONING_HEADERS:
        # Simplify the check to a straightforward string containment
        if f"{header}".lower() not in content.lower():
            missing.append(header)
    
    if not missing:
        print("PASS: Standard reasoning headers compliant.")
        return True
    else:
        print(f"FAILED: Mandatory sections missing from reasoning.md: {missing}")
        return False

def main():
    print("=== NFLStatsPro V3 Swarm Auditor (v1.1) ===")
    results = [
        audit_data_integrity(),
        audit_midnight_slate(),
        audit_protocol()
    ]
    
    if all(results):
        print("\nPASS: Swarm is in High-Hardness state.")
        sys.exit(0)
    else:
        print("\nSWARM HARDENING DEFICIENT. Address failures above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
