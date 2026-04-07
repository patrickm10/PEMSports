import json
import base64
from backend.services.position_helper import PredicateParser

def test_sql_injection():
    # Attempt a basic SQL injection
    malicious_filter = {
        "conjunction": "AND",
        "conditions": [
            {"field": "Rank", "operator": "eq", "value": "1\" OR 1=1 --"}
        ]
    }
    
    # Mock column names
    column_names = ["Rank", "Player", "Score"]
    
    try:
        sql, params = PredicateParser.parse(malicious_filter, column_names)
        print(f"Generated SQL: {sql}")
        print(f"Parameters: {params}")
        
        # In a parameterized world, the SQL should NOT contain the malicious string
        if "1=1" in sql or "--" in sql:
            print("VULNERABILITY CONFIRMED: SQL Injection possible.")
        elif "?" in sql and params[0] == malicious_filter["conditions"][0]["value"]:
            print("SUCCESS: SQL is parameterized. Injection neutralized.")
        else:
            print("Check generated SQL structure manually.")
    except Exception as e:
        print(f"Parser failed: {e}")

def test_logical_order():
    # Test if conjunctions are wrapped properly for multi-part WHERE clauses
    filter_obj = {
        "conjunction": "OR",
        "conditions": [
            {"field": "Player", "operator": "contains", "value": "Allen"},
            {"field": "Player", "operator": "contains", "value": "Mahomes"}
        ]
    }
    column_names = ["Player", "Rank"]
    sql, params = PredicateParser.parse(filter_obj, column_names)
    print(f"Generated OR SQL: {sql}")
    
    # With the new AST, it should be (Condition) OR (Condition)
    if sql.count("(") >= 2 and " OR " in sql:
        print("SUCCESS: Logical OR is correctly grouped with parentheses.")
    else:
        print(f"FAILURE: Logical grouping missing or incorrect: {sql}")

if __name__ == "__main__":
    print("--- Testing V3 Hardened Predicate Parser ---")
    test_sql_injection()
    print("\n--- Testing Logical Grouping ---")
    test_logical_order()
