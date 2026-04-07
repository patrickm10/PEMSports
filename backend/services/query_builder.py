from dataclasses import dataclass, field
from typing import List, Any, Tuple, Dict, Union, Optional

@dataclass
class ExpressionNode:
    """Base class for all filter expressions."""
    pass

@dataclass
class ConditionNode(ExpressionNode):
    """Leaf node for a single column/value filter."""
    column: str
    operator: str
    value: Any

@dataclass
class LogicalNode(ExpressionNode):
    """Group node for logical conjunctions (AND/OR)."""
    conjunction: str
    nodes: List[ExpressionNode]

class ASTCompiler:
    """Compiles an AST into a parameterized SQL fragment for DuckDB."""
    
    OPERATORS = {
        "eq": "=",
        "neq": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "contains": "LIKE",
        "in": "IN"
    }

    @classmethod
    def compile(cls, node: ExpressionNode) -> Tuple[str, List[Any]]:
        """Recursively compile the AST into (sql_template, params)."""
        if isinstance(node, ConditionNode):
            return cls._compile_condition(node)
        elif isinstance(node, LogicalNode):
            return cls._compile_logical(node)
        return ("1=1", [])

    @classmethod
    def _compile_condition(cls, node: ConditionNode) -> Tuple[str, List[Any]]:
        op = cls.OPERATORS.get(node.operator.lower(), "=")
        sql_val = "?"
        
        # Specific formatting for LIKE/IN
        if op == "LIKE":
            val = f"%{node.value}%"
        elif op == "IN":
            if not isinstance(node.value, list):
                val = [node.value]
            else:
                val = node.value
            sql_val = f"({', '.join(['?' for _ in val])})"
            return f"\"{node.column}\" {op} {sql_val}", val
        else:
            val = node.value
            
        return f"\"{node.column}\" {op} {sql_val}", [val]

    @classmethod
    def _compile_logical(cls, node: LogicalNode) -> Tuple[str, List[Any]]:
        if not node.nodes:
            return ("1=1", [])
            
        parts = []
        all_params = []
        for child in node.nodes:
            sql, params = cls.compile(child)
            parts.append(f"({sql})")
            all_params.extend(params)
            
        conjunction = f" {node.conjunction.upper()} "
        return conjunction.join(parts), all_params

    @classmethod
    def from_dict(cls, filter_obj: Dict[str, Any], column_names: List[str]) -> ExpressionNode:
        """Parses the V3 JSON filter structure into an AST."""
        if not filter_obj or "conditions" not in filter_obj:
            return LogicalNode("AND", [])
            
        # Case-insensitive mapping for columns
        col_map = {c.lower(): c for c in column_names}
        conjunction = filter_obj.get("conjunction", "AND").upper()
        
        nodes = []
        for cond in filter_obj.get("conditions", []):
            if "conditions" in cond:
                # Nested logical grouping
                nodes.append(cls.from_dict(cond, column_names))
            else:
                # Standard leaf condition
                field_raw = cond.get("field", "").lower()
                field = col_map.get(field_raw, field_raw)
                nodes.append(ConditionNode(
                    column=field,
                    operator=cond.get("operator", "eq"),
                    value=cond.get("value")
                ))
                
        return LogicalNode(conjunction, nodes)
