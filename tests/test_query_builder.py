import pytest
from backend.services.query_builder import ASTCompiler, ConditionNode, LogicalNode

def test_basic_condition():
    node = ConditionNode("Rank", "eq", 1)
    sql, params = ASTCompiler.compile(node)
    assert sql == '"Rank" = ?'
    assert params == [1]

def test_like_condition():
    node = ConditionNode("Player", "contains", "Allen")
    sql, params = ASTCompiler.compile(node)
    assert sql == '"Player" LIKE ?'
    assert params == ["%Allen%"]

def test_in_condition():
    node = ConditionNode("team_name", "in", ["BUF", "KC"])
    sql, params = ASTCompiler.compile(node)
    assert sql == '"team_name" IN (?, ?)'
    assert params == ["BUF", "KC"]

def test_and_logical_grouping():
    cond1 = ConditionNode("year", "eq", 2024)
    cond2 = ConditionNode("week", "eq", 1)
    node = LogicalNode("AND", [cond1, cond2])
    sql, params = ASTCompiler.compile(node)
    assert sql == '("year" = ?) AND ("week" = ?)'
    assert params == [2024, 1]

def test_nested_or_grouping():
    # Test (year = 2024) AND (Player = 'Allen' OR Player = 'Mahomes')
    year_cond = ConditionNode("year", "eq", 2024)
    p1 = ConditionNode("Player", "contains", "Allen")
    p2 = ConditionNode("Player", "contains", "Mahomes")
    or_group = LogicalNode("OR", [p1, p2])
    
    root = LogicalNode("AND", [year_cond, or_group])
    sql, params = ASTCompiler.compile(root)
    
    # Precedence check: The OR should be wrapped in parentheses
    assert sql == '("year" = ?) AND (("Player" LIKE ?) OR ("Player" LIKE ?))'
    assert params == [2024, "%Allen%", "%Mahomes%"]

def test_from_dict_parsing():
    filter_obj = {
        "conjunction": "OR",
        "conditions": [
            {"field": "Player", "operator": "eq", "value": "Josh Allen"},
            {"field": "Player", "operator": "eq", "value": "Patrick Mahomes"}
        ]
    }
    column_names = ["Player", "Rank"]
    node = ASTCompiler.from_dict(filter_obj, column_names)
    assert isinstance(node, LogicalNode)
    assert node.conjunction == "OR"
    assert len(node.nodes) == 2
    
    sql, params = ASTCompiler.compile(node)
    assert sql == '("Player" = ?) OR ("Player" = ?)'
    assert params == ["Josh Allen", "Patrick Mahomes"]

def test_sql_injection_prevention():
    # Malicious string designed to break out of single quotes if not parameterized
    malicious_val = "1\" OR 1=1 --"
    node = ConditionNode("Rank", "eq", malicious_val)
    sql, params = ASTCompiler.compile(node)
    
    # The SQL should still have a single placeholder, and the value should be in params
    assert sql == '"Rank" = ?'
    assert params == [malicious_val]

def test_case_insensitive_mapping():
    filter_obj = {
        "conditions": [{"field": "rank", "operator": "eq", "value": 1}]
    }
    # Provided column name is "Rank" (Capitalized)
    column_names = ["Rank", "Player"]
    node = ASTCompiler.from_dict(filter_obj, column_names)
    assert isinstance(node.nodes[0], ConditionNode)
    assert node.nodes[0].column == "Rank" # Mapped to correct casing
